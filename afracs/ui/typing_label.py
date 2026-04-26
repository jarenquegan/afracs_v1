"""QLabel that types and erases through a list of strings."""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel

TYPE_INTERVAL_MS = 80
ERASE_INTERVAL_MS = 45
HOLD_FULL_MS = 6_000
HOLD_EMPTY_MS = 900


class TypingLabel(QLabel):
    def __init__(self, strings: list[str], parent=None) -> None:
        super().__init__(parent)
        self._strings = list(strings)
        self._idx = 0
        self._buf = ""
        self._typing = True

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(TYPE_INTERVAL_MS)

    def _step(self) -> None:
        target = self._strings[self._idx]
        if self._typing:
            if len(self._buf) < len(target):
                self._buf = target[: len(self._buf) + 1]
                self.setText(self._buf)
                self._timer.start(TYPE_INTERVAL_MS)
                return
            self._typing = False
            self._timer.start(HOLD_FULL_MS)
            return

        if self._buf:
            self._buf = self._buf[:-1]
            self.setText(self._buf)
            self._timer.start(ERASE_INTERVAL_MS)
            return

        self._idx = (self._idx + 1) % len(self._strings)
        self._typing = True
        self._timer.start(HOLD_EMPTY_MS)
