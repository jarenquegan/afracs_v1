"""Self-updating clock/date labels and StableLabel utility."""

from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel


class StableLabel(QLabel):
    """QLabel whose setText() never triggers a layout recalculation.

    Use for any label whose text changes on a timer — clocks, countdowns,
    typing animations. Without this, every setText() calls updateGeometry()
    which propagates layout changes up the entire widget tree, causing
    continuous repaints and visible jitter on the Pi.
    """
    def updateGeometry(self) -> None:
        pass


class ClockLabel(StableLabel):
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


class DateLabel(StableLabel):
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
