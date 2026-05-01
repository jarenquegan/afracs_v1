"""Persistent bottom status bar."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from afracs import config
from afracs.ui.clock import ClockLabel
from afracs.ui.typing_label import TypingLabel

_TIPS: list[str] = [
    "Position your face within the frame to begin verification",
    "Only registered College of Health faculty may access this cabinet",
    "All access attempts are logged with timestamps",
    "Unauthorized access triggers a security alert after 5 attempts",
    "Tap the screen or press the button to start face verification",
    "For registration or access issues, contact the College of Health office",
    "Keep the camera area clean and well-lit for best results",
    "Face verification typically completes in under 3 seconds",
]


def _sep() -> QLabel:
    label = QLabel("|")
    label.setObjectName("statusBarSep")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class StatusBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        self._info = QLabel()
        self._info.setObjectName("statusBarInfo")
        self._info.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._info)

        layout.addWidget(_sep())

        self._tip = TypingLabel(_TIPS)
        self._tip.setObjectName("statusBarTip")
        self._tip.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        # Ignored width: layout owns the tip's width via stretch. Without this,
        # longer tip text would shrink the info/datetime labels next to it.
        self._tip.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._tip, stretch=1)

        layout.addWidget(_sep())

        self._datetime = ClockLabel(time_format="%a, %b %d  ·  %H:%M:%S")
        self._datetime.setObjectName("statusBarDateTime")
        self._datetime.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._datetime)

        self._lock_secured = True
        self._system_online = True
        self._refresh()

    def set_lock_secured(self, secured: bool) -> None:
        self._lock_secured = secured
        self._refresh()

    def set_system_online(self, online: bool) -> None:
        self._system_online = online
        self._refresh()

    def _refresh(self) -> None:
        lock = "Secured" if self._lock_secured else "Open"
        status = "Online" if self._system_online else "Offline"
        self._info.setText(
            f"●  {config.CABINET_NAME}  ·  Lock: {lock}  ·  {status}  "
        )
