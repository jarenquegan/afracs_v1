"""Self-updating clock and date labels."""

from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel


class ClockLabel(QLabel):
    def __init__(self, time_format: str = "%H:%M:%S", parent=None) -> None:
        super().__init__(parent)
        self._format = time_format
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tick()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self) -> None:
        self.setText(datetime.now().strftime(self._format))


class DateLabel(QLabel):
    def __init__(self, date_format: str = "%A, %B %d", parent=None) -> None:
        super().__init__(parent)
        self._format = date_format
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tick()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60_000)

    def _tick(self) -> None:
        self.setText(datetime.now().strftime(self._format))
