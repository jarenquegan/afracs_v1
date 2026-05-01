"""ALERT state widget: lockout after repeated unauthorized attempts."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from afracs.ui.clock import StableLabel

from afracs import config

COOLDOWN_SECONDS = 60


class AlertPage(QWidget):
    return_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("alertPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        body = QVBoxLayout()
        body.setContentsMargins(0, 24, 0, 24)
        body.setSpacing(8)
        body.addStretch(1)

        glyph = QLabel("⚠")
        glyph.setObjectName("bigGlyph")
        glyph.setProperty("state", "alert")
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(glyph)

        title = QLabel("Cabinet Locked")
        title.setObjectName("stateTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(title)

        reason = QLabel(
            f"{config.ALERT_AFTER_FAILED_ATTEMPTS} unauthorized attempts detected"
        )
        reason.setObjectName("stateBody")
        reason.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(reason)

        notify = QLabel("Administrator has been notified")
        notify.setObjectName("stateBody")
        notify.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(notify)

        body.addSpacing(12)

        self.cooldown_label = StableLabel()
        self.cooldown_label.setObjectName("stateMeta")
        self.cooldown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.cooldown_label)

        body.addStretch(2)
        layout.addLayout(body, stretch=1)

        self._remaining = COOLDOWN_SECONDS
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)

    def enter(self, **_ctx) -> None:
        self._remaining = COOLDOWN_SECONDS
        self._refresh_label()
        self._tick_timer.start(1000)

    def leave(self) -> None:
        self._tick_timer.stop()

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self._tick_timer.stop()
            self.return_requested.emit()
            return
        self._refresh_label()

    def _refresh_label(self) -> None:
        self.cooldown_label.setText(f"Cooldown: {self._remaining}s before next attempt")
