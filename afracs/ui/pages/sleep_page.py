"""SLEEP state widget: lockscreen with clock, date, tap-to-wake, status dots."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from afracs import config
from afracs.ui.clock import ClockLabel, DateLabel, StableLabel


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
        body_layout.setContentsMargins(0, 40, 0, 24)
        body_layout.setSpacing(12)
        body_layout.addStretch(1)

        self.clock = ClockLabel("%H:%M")
        self.clock.setObjectName("sleepClock")
        body_layout.addWidget(self.clock)

        self.date = DateLabel("%A, %B %d, %Y")
        self.date.setObjectName("sleepDate")
        body_layout.addWidget(self.date)

        body_layout.addSpacing(36)

        self.wake_button = QPushButton("Tap to Access")
        self.wake_button.setObjectName("sleepWakeButton")
        self.wake_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wake_button.clicked.connect(self.wake_requested)
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.wake_button)
        button_row.addStretch(1)
        body_layout.addLayout(button_row)

        body_layout.addStretch(2)

        self.status_dot = StableLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(self.status_dot)

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
