"""SLEEP state widget: lockscreen with clock, date, tap-to-wake, status dots.

Uses absolute positioning (no layout) for the page contents. Qt layouts in PyQt6
re-trigger geometry recalculations from internal C++ paths that bypass any
Python-level overrides — the only bulletproof fix is to take the layout system
out of the loop entirely. resizeEvent positions every child widget by hand
based on percentages of the page size, so once the page receives a stable
geometry from its parent it never reflows.
"""

from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QPushButton, QWidget

from afracs import config, theme
from afracs.ui.clock import StableLabel


class _ClockWidget(QWidget):
    """Renders clock + date entirely via paintEvent. Font sizes scale to widget
    height so layout fluctuations would only smoothly rescale, not jump."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._time_str = ""
        self._date_str = ""
        self._tick()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self) -> None:
        now = datetime.now()
        new_time = now.strftime("%H:%M")
        new_date = now.strftime("%A, %B %d, %Y")
        if new_time == self._time_str and new_date == self._date_str:
            return
        self._time_str = new_time
        self._date_str = new_date
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        clock_h = int(h * 0.66)
        date_h = h - clock_h

        clock_font = QFont(theme.FONT_FAMILY)
        clock_font.setPixelSize(max(48, int(clock_h * 0.78)))
        clock_font.setWeight(QFont.Weight.Bold)
        painter.setFont(clock_font)
        painter.setPen(QColor(theme.GOLD))
        painter.drawText(0, 0, w, clock_h, Qt.AlignmentFlag.AlignCenter, self._time_str)

        date_font = QFont(theme.FONT_FAMILY)
        date_font.setPixelSize(max(14, int(date_h * 0.32)))
        date_font.setWeight(QFont.Weight.Light)
        painter.setFont(date_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(0, clock_h, w, date_h, Qt.AlignmentFlag.AlignCenter, self._date_str)


class SleepPage(QWidget):
    wake_requested  = pyqtSignal()
    admin_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sleepPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._clock = _ClockWidget(self)

        self.wake_button = QPushButton("Tap to Access", self)
        self.wake_button.setObjectName("sleepWakeButton")
        self.wake_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wake_button.clicked.connect(self.wake_requested)

        self.status_dot = StableLabel(self)
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.admin_button = QPushButton("⚙  Admin", self)
        self.admin_button.setObjectName("adminButton")
        self.admin_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.admin_button.clicked.connect(self._on_admin_clicked)

        self._lock_secured = True
        self._system_online = True
        self._refresh_status_dot()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        # Clock occupies the top 60% of the page (clock + date drawn inside)
        clock_h = int(h * 0.60)
        self._clock.setGeometry(0, 0, w, clock_h)

        # Wake button: ~30% width, sized by font, centered horizontally
        btn_w = max(260, int(w * 0.28))
        btn_h = max(54, int(h * 0.09))
        btn_y = int(h * 0.66)
        self.wake_button.setGeometry((w - btn_w) // 2, btn_y, btn_w, btn_h)

        # Status dots row near bottom
        status_h = max(20, int(h * 0.05))
        status_y = int(h * 0.82)
        self.status_dot.setGeometry(0, status_y, w, status_h)

        # Admin button: bottom-right corner
        admin_w = max(90, int(w * 0.08))
        admin_h = max(28, int(h * 0.045))
        self.admin_button.setGeometry(
            w - admin_w - 16,
            h - admin_h - 12,
            admin_w,
            admin_h,
        )

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
        # Don't fire wake when admin button itself is clicked
        child = self.childAt(event.position().toPoint())
        if child is self.admin_button:
            return super().mousePressEvent(event)
        self.wake_requested.emit()
        super().mousePressEvent(event)

    def enter(self, **_ctx) -> None:
        pass

    def leave(self) -> None:
        pass
