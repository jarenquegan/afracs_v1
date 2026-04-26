"""GRANTED state widget."""

from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

AUTO_RETURN_SECONDS = 3


class GrantedPage(QWidget):
    return_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("grantedPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        body = QVBoxLayout()
        body.setContentsMargins(0, 24, 0, 24)
        body.setSpacing(8)
        body.addStretch(1)

        glyph = QLabel("✓")
        glyph.setObjectName("bigGlyph")
        glyph.setProperty("state", "granted")
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(glyph)

        self.name = QLabel()
        self.name.setObjectName("stateTitle")
        self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.name)

        self.role = QLabel()
        self.role.setObjectName("stateBody")
        self.role.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.role)

        body.addSpacing(12)

        self.meta = QLabel()
        self.meta.setObjectName("stateMeta")
        self.meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.meta)

        self.countdown = QLabel()
        self.countdown.setObjectName("stateCountdown")
        self.countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.countdown)

        body.addStretch(2)
        layout.addLayout(body, stretch=1)

        self._remaining = AUTO_RETURN_SECONDS
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)

    def enter(self, *, name: str = "Faculty", role: str = "College of Health Faculty", cabinet: str = "", **_ctx) -> None:
        now = datetime.now().strftime("%I:%M %p").lstrip("0")
        self.name.setText(f"Welcome, {name}")
        self.role.setText(role)
        self.meta.setText(f"Access granted at {now}")
        self._remaining = AUTO_RETURN_SECONDS
        self._refresh_countdown(cabinet)
        self._tick_timer.start(1000)

    def leave(self) -> None:
        self._tick_timer.stop()

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self._tick_timer.stop()
            self.return_requested.emit()
            return
        self._refresh_countdown(self._cabinet)

    def _refresh_countdown(self, cabinet: str = "") -> None:
        self._cabinet = cabinet
        cab_label = f"Cabinet {cabinet}  ·  " if cabinet else ""
        self.countdown.setText(f"{cab_label}Returning in {self._remaining}s")
