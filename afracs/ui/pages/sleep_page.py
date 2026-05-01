"""SLEEP state widget: lockscreen with clock, date, tap-to-wake, status dots."""

from datetime import datetime

from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from afracs import config, theme
from afracs.ui.clock import StableLabel


class _ClockWidget(QWidget):
    """Draws the clock via paintEvent so it NEVER touches the layout system.

    QLabel.setText() calls updateGeometry() which propagates layout recalculation
    up the widget tree, causing the body stretches to redistribute and the clock
    to visually jump in size every second. paintEvent + update() has no layout side
    effects whatsoever.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._time_str = ""
        self._date_str = ""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._tick()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self) -> None:
        now = datetime.now()
        self._time_str = now.strftime("%H:%M")
        self._date_str = now.strftime("%A, %B %d, %Y")
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()

        # Clock
        clock_font = QFont(theme.FONT_FAMILY)
        clock_font.setPixelSize(theme.FontSize.LOCK_CLOCK)
        clock_font.setWeight(QFont.Weight.Bold)
        painter.setFont(clock_font)
        painter.setPen(QColor(theme.GOLD))
        clock_rect_h = round(h * 0.55)
        painter.drawText(0, 0, w, clock_rect_h, Qt.AlignmentFlag.AlignCenter, self._time_str)

        # Date
        date_font = QFont(theme.FONT_FAMILY)
        date_font.setPixelSize(theme.FontSize.LOCK_DATE)
        date_font.setWeight(QFont.Weight.Light)
        painter.setFont(date_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(0, clock_rect_h, w, h - clock_rect_h, Qt.AlignmentFlag.AlignCenter, self._date_str)

    def sizeHint(self) -> QSize:
        return QSize(0, 0)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)


class SleepPage(QWidget):
    wake_requested  = pyqtSignal()
    admin_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sleepPage")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Clock+date as one paint widget — completely layout-immune
        self._clock_widget = _ClockWidget()
        body_layout.addWidget(self._clock_widget, stretch=3)

        self.wake_button = QPushButton("Tap to Access")
        self.wake_button.setObjectName("sleepWakeButton")
        self.wake_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wake_button.clicked.connect(self.wake_requested)
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.wake_button)
        button_row.addStretch(1)
        body_layout.addLayout(button_row)

        body_layout.addSpacing(theme.Space.SM)

        self.status_dot = StableLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(self.status_dot)

        body_layout.addStretch(1)

        outer.addWidget(body, stretch=1)

        admin_row = QHBoxLayout()
        admin_row.setContentsMargins(0, 0, 16, 10)
        admin_row.addStretch(1)
        self.admin_button = QPushButton("⚙  Admin")
        self.admin_button.setObjectName("adminButton")
        self.admin_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.admin_button.clicked.connect(self._on_admin_clicked)
        admin_row.addWidget(self.admin_button)
        outer.addLayout(admin_row)

        self._lock_secured = True
        self._system_online = True
        self._refresh_status_dot()

    def _on_admin_clicked(self) -> None:
        self.admin_requested.emit()

    def set_lock_secured(self, secured: bool) -> None:
        self._lock_secured = secured
        self._refresh_status_dot()

    def set_system_online(self, online: bool) -> None:
        self._system_online = online
        self._refresh_status_dot()

    def _refresh_status_dot(self) -> None:
        lock = "Secured" if self._lock_secured else "Open"
        sys_state = "Online" if self._system_online else "Offline"
        self.status_dot.setText(
            f"●  {config.CABINET_NAME}    ●  {lock}    ●  {sys_state}"
        )

    def mousePressEvent(self, event) -> None:
        self.wake_requested.emit()
        super().mousePressEvent(event)

    def enter(self, **_ctx) -> None:
        pass

    def leave(self) -> None:
        pass
