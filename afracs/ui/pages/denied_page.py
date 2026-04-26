"""DENIED state widget."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from afracs import config

AUTO_RETURN_SECONDS = 2


class DeniedPage(QWidget):
    return_requested = pyqtSignal()
    retry_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("deniedPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        body = QVBoxLayout()
        body.setContentsMargins(0, 24, 0, 24)
        body.setSpacing(8)
        body.addStretch(1)

        glyph = QLabel("✗")
        glyph.setObjectName("bigGlyph")
        glyph.setProperty("state", "denied")
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(glyph)

        title = QLabel("Access Denied")
        title.setObjectName("stateTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(title)

        sub = QLabel("Face not recognized")
        sub.setObjectName("stateBody")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(sub)

        body.addSpacing(12)

        self.attempt_meta = QLabel()
        self.attempt_meta.setObjectName("stateMeta")
        self.attempt_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.attempt_meta)

        self.countdown = QLabel()
        self.countdown.setObjectName("stateCountdown")
        self.countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.countdown)

        body.addSpacing(16)

        retry_row = QHBoxLayout()
        retry_row.addStretch(1)
        self.retry_btn = QPushButton("Try Again")
        self.retry_btn.setObjectName("retryButton")
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.clicked.connect(self.retry_requested)
        retry_row.addWidget(self.retry_btn)
        retry_row.addStretch(1)
        body.addLayout(retry_row)

        body.addStretch(2)
        layout.addLayout(body, stretch=1)

        self._remaining = AUTO_RETURN_SECONDS
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)

    def enter(self, *, attempt: int = 1, **_ctx) -> None:
        max_attempts = config.ALERT_AFTER_FAILED_ATTEMPTS
        self.attempt_meta.setText(f"Attempt {attempt} of {max_attempts}")
        self._remaining = AUTO_RETURN_SECONDS
        self._refresh_countdown()
        self._tick_timer.start(1000)

    def leave(self) -> None:
        self._tick_timer.stop()

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self._tick_timer.stop()
            self.return_requested.emit()
            return
        self._refresh_countdown()

    def _refresh_countdown(self) -> None:
        self.countdown.setText(f"Returning to camera in {self._remaining}s")
