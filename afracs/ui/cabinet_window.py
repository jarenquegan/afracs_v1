"""Cabinet touchscreen UI: state-driven QStackedWidget shell.

States: SLEEP, DETECTING, SELECTING, GRANTED, DENIED, ALERT.

Dev shortcuts: T wake, G grant, D deny, A alert, S/Esc sleep,
L toggle lock indicator, F11 fullscreen.
"""

import logging
import sys
from enum import Enum, auto

import cv2
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from afracs import config, db, theme
from afracs.ui.fonts import install_fonts
from afracs.ui.header_bar import HeaderBar
from afracs.ui.pages import (
    AlertPage,
    DeniedPage,
    DetectingPage,
    GrantedPage,
    SelectingPage,
    SleepPage,
)
from afracs.ui.status_bar import StatusBar
from afracs.ui.styles import make_qss

log = logging.getLogger(__name__)

_RECOGNITION_EVERY_N = 3


class State(Enum):
    SLEEP = auto()
    DETECTING = auto()
    SELECTING = auto()
    GRANTED = auto()
    DENIED = auto()
    ALERT = auto()


LIVE_CAMERA_STATES = {State.DETECTING, State.DENIED}


class CabinetWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"AFRACS — {config.CABINET_NAME}")
        self.setStyleSheet(make_qss())

        self._failed_attempts = 0
        self._cap: cv2.VideoCapture | None = None

        self._engine = None
        self._known_faces: list[dict] = []
        self._db_conn = None
        self._cabinet_info: dict[str, str] = {}

        self._lock_bank = None

        self._frame_count = 0
        self._match_streak = 0
        self._streak_id: int | None = None
        self._no_match_frames = 0

        self._pending_faculty: dict | None = None

        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._update_camera_frame)

        self._build_ui()
        self._wire_pages()
        self._wire_shortcuts()
        self._state: State | None = None
        self.set_state(State.SLEEP)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = HeaderBar()
        layout.addWidget(self.header)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, stretch=1)

        self.sleep_page = SleepPage()
        self.detecting_page = DetectingPage()
        self.selecting_page = SelectingPage()
        self.granted_page = GrantedPage()
        self.denied_page = DeniedPage()
        self.alert_page = AlertPage()

        self._pages: dict[State, QWidget] = {
            State.SLEEP: self.sleep_page,
            State.DETECTING: self.detecting_page,
            State.SELECTING: self.selecting_page,
            State.GRANTED: self.granted_page,
            State.DENIED: self.denied_page,
            State.ALERT: self.alert_page,
        }
        for page in self._pages.values():
            self.stack.addWidget(page)

        border = QFrame()
        border.setObjectName("statusBarBorder")
        border.setFixedHeight(2)
        layout.addWidget(border)

        self.status_bar = StatusBar()
        layout.addWidget(self.status_bar)

        self.setCentralWidget(root)

    def _wire_pages(self) -> None:
        self.sleep_page.wake_requested.connect(self.wake)
        self.sleep_page.admin_requested.connect(self._open_admin_panel)
        self.detecting_page.cancel_requested.connect(lambda: self.set_state(State.SLEEP))
        self.selecting_page.cabinet_selected.connect(self._on_cabinet_selected)
        self.selecting_page.cancel_requested.connect(lambda: self.set_state(State.SLEEP))
        self.granted_page.return_requested.connect(lambda: self.set_state(State.SLEEP))
        self.denied_page.return_requested.connect(self._after_denied)
        self.denied_page.retry_requested.connect(lambda: self.set_state(State.DETECTING))
        self.alert_page.return_requested.connect(self._after_alert)

    def _wire_shortcuts(self) -> None:
        for key, handler in [
            ("T", self.wake),
            ("G", lambda: self._dev_grant()),
            ("D", lambda: self._dev_deny()),
            ("A", lambda: self.set_state(State.ALERT)),
            ("S", lambda: self.set_state(State.SLEEP)),
            ("Escape", lambda: self.set_state(State.SLEEP)),
            ("L", self._toggle_lock_indicator),
            ("F11", self._toggle_fullscreen),
        ]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(handler)

    def wake(self) -> None:
        if self._state is State.SLEEP:
            self._failed_attempts = 0
            self.set_state(State.DETECTING)

    def set_state(self, state: State, **ctx) -> None:
        prev = self._state
        if prev is not None:
            self._pages[prev].leave()

        prev_live = prev in LIVE_CAMERA_STATES if prev is not None else False
        next_live = state in LIVE_CAMERA_STATES
        if next_live and not prev_live:
            self._open_camera()
            self._init_engine()
        elif prev_live and not next_live:
            self._close_camera()

        if state is State.DETECTING:
            self._frame_count = 0
            self._match_streak = 0
            self._streak_id = None
            self._no_match_frames = 0
            self._pending_faculty = None
            self._reload_known_faces()
            self._load_cabinet_info()

        self._state = state
        page = self._pages[state]
        page.enter(**ctx)
        self.stack.setCurrentWidget(page)

    def _on_cabinet_selected(self, cabinet_id: str) -> None:
        faculty = self._pending_faculty
        if faculty is None:
            self.set_state(State.SLEEP)
            return

        self._failed_attempts = 0
        self._log_access(faculty["id"], "granted", f"Cabinet {cabinet_id}")
        self._fire_lock(cabinet_id)
        self.set_state(
            State.GRANTED,
            name=faculty["name"],
            role=faculty["role"],
            cabinet=cabinet_id,
        )

    def _init_engine(self) -> None:
        if self._engine is not None:
            return
        try:
            from afracs.recognition import FaceEngine
            self._engine = FaceEngine()
        except FileNotFoundError as exc:
            log.warning("FaceEngine unavailable: %s", exc)
            self._engine = None

    def _reload_known_faces(self) -> None:
        try:
            if self._db_conn is None or not self._db_conn.open:
                self._db_conn = db.connect()
            rows = db.load_known_faces(self._db_conn)
        except Exception as exc:
            log.warning("Could not load known faces from DB: %s", exc)
            rows = []

        if rows and self._engine is not None:
            from afracs.recognition import decode_known_faces
            self._known_faces = decode_known_faces(rows)
        else:
            self._known_faces = []

        log.info("Loaded %d known face(s)", len(self._known_faces))

    def _load_cabinet_info(self) -> None:
        try:
            if self._db_conn is None or not self._db_conn.open:
                self._db_conn = db.connect()
            self._cabinet_info = {
                r["cabinet_id"]: r.get("description", r["cabinet_id"])
                for r in db.get_cabinets(self._db_conn)
            }
        except Exception as exc:
            log.warning("Could not load cabinet info: %s", exc)

    def _log_access(self, faculty_id: int | None, status: str, note: str = "") -> None:
        try:
            if self._db_conn is None or not self._db_conn.open:
                self._db_conn = db.connect()
            db.log_access(self._db_conn, faculty_id, note.replace("Cabinet ", "") or config.CABINET_NAME, status, note)
        except Exception as exc:
            log.warning("Could not log access event: %s", exc)

    def _init_locks(self) -> None:
        if self._lock_bank is not None or not config.CABINET_LOCK_PINS:
            return
        try:
            from afracs.hardware import CabinetLockBank
            self._lock_bank = CabinetLockBank()
            log.info("Lock bank initialised for cabinets: %s", list(config.CABINET_LOCK_PINS))
        except Exception as exc:
            log.warning("Could not init lock bank: %s", exc)

    def _fire_lock(self, cabinet_id: str) -> None:
        self._init_locks()
        if self._lock_bank is not None:
            self._lock_bank.unlock(cabinet_id)

    def _open_camera(self) -> None:
        if self._cap is not None:
            return
        self._cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not self._cap.isOpened():
            self._cap.release()
            self._cap = None
            self.detecting_page.show_unavailable()
            return
        self._frame_timer.start(33)

    def _close_camera(self) -> None:
        self._frame_timer.stop()
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _update_camera_frame(self) -> None:
        if self._cap is None or self._state is not State.DETECTING:
            return
        ok, frame = self._cap.read()
        if not ok:
            return

        self._frame_count += 1

        if self._engine is not None and self._frame_count % _RECOGNITION_EVERY_N == 0:
            result = self._engine.process_frame(frame, self._known_faces)
            self._handle_recognition(result)

        self.detecting_page.show_frame(frame)

    def _handle_recognition(self, result) -> None:
        if not result.face_found:
            self._match_streak = 0
            self._no_match_frames = 0
            return

        self.detecting_page.face_detected()

        if result.matched:
            if self._streak_id is None or self._streak_id == result.faculty_id:
                self._streak_id = result.faculty_id
                self._match_streak += 1
                self._no_match_frames = 0
            else:
                self._match_streak = 1
                self._streak_id = result.faculty_id
                self._no_match_frames = 0

            if self._match_streak >= config.RECOGNITION_STREAK:
                accessible = [c for c in result.cabinets]
                if not accessible:
                    self._failed_attempts += 1
                    self._log_access(result.faculty_id, "denied", "No cabinet access assigned")
                    self.set_state(State.DENIED, attempt=self._failed_attempts)
                elif len(accessible) == 1:
                    self._failed_attempts = 0
                    cabinet_id = accessible[0]
                    self._log_access(result.faculty_id, "granted", f"Cabinet {cabinet_id}")
                    self._fire_lock(cabinet_id)
                    self.set_state(
                        State.GRANTED,
                        name=result.name,
                        role=result.role,
                        cabinet=cabinet_id,
                    )
                else:
                    self._pending_faculty = {
                        "id": result.faculty_id,
                        "name": result.name,
                        "role": result.role,
                    }
                    cab_list = [
                        {"id": c, "description": self._cabinet_info.get(c, c)}
                        for c in accessible
                    ]
                    self.set_state(
                        State.SELECTING,
                        name=result.name,
                        cabinets=cab_list,
                    )
        else:
            self._match_streak = 0
            self._streak_id = None
            self._no_match_frames += 1
            if self._no_match_frames >= config.UNRECOGNISED_DENY_FRAMES:
                self._failed_attempts += 1
                self._log_access(None, "denied", f"confidence={result.confidence:.3f}")
                self.set_state(State.DENIED, attempt=self._failed_attempts)

    def _after_denied(self) -> None:
        if self._failed_attempts >= config.ALERT_AFTER_FAILED_ATTEMPTS:
            self.set_state(State.ALERT)
        else:
            self.set_state(State.DETECTING)

    def _after_alert(self) -> None:
        self._failed_attempts = 0
        self.set_state(State.SLEEP)

    def _dev_grant(self) -> None:
        self._failed_attempts = 0
        self.set_state(State.GRANTED, name="Dr. Cruz", role="College of Health Faculty", cabinet="A")

    def _dev_deny(self) -> None:
        self._failed_attempts += 1
        self.set_state(State.DENIED, attempt=self._failed_attempts)

    def _toggle_lock_indicator(self) -> None:
        secured = not self.sleep_page._lock_secured
        self.sleep_page.set_lock_secured(secured)
        self.status_bar.set_lock_secured(secured)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _open_admin_panel(self) -> None:
        import webbrowser
        url = f"http://127.0.0.1:{config.FLASK_PORT}"
        webbrowser.open(url)

    def closeEvent(self, event) -> None:
        self._close_camera()
        if self._lock_bank is not None:
            try:
                self._lock_bank.close()
            except Exception:
                pass
        if self._db_conn is not None:
            try:
                self._db_conn.close()
            except Exception:
                pass
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)

    screen = app.primaryScreen()
    geom = screen.availableGeometry()
    # Reference design: 960×600. Scale all tokens to match actual screen.
    scale = min(geom.width() / 960, geom.height() / 600)
    theme.rescale(scale)

    family = install_fonts() or theme.FONT_FAMILY
    base_font_size = max(8, round(11 * scale))
    app.setFont(QFont(family, base_font_size))

    win = CabinetWindow()
    win.showFullScreen()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
