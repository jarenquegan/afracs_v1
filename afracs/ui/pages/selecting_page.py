"""SELECTING state widget: cabinet picker for faculty with multiple cabinet access."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

IDLE_SECONDS = 30


class SelectingPage(QWidget):
    cabinet_selected = pyqtSignal(str)
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("selectingPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        body = QVBoxLayout()
        body.setContentsMargins(0, 24, 0, 24)
        body.setSpacing(8)
        body.addStretch(1)

        self._greeting = QLabel()
        self._greeting.setObjectName("stateTitle")
        self._greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self._greeting)

        prompt = QLabel("Which cabinet would you like to open?")
        prompt.setObjectName("stateBody")
        prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(prompt)

        body.addSpacing(20)

        self._btn_row = QHBoxLayout()
        self._btn_row.setSpacing(12)
        self._btn_row.addStretch(1)
        self._btn_row_end_stretch_index = None
        body.addLayout(self._btn_row)

        body.addSpacing(16)

        cancel_row = QHBoxLayout()
        cancel_row.addStretch(1)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancelButton")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self.cancel_requested)
        cancel_row.addWidget(self._cancel_btn)
        cancel_row.addStretch(1)
        body.addLayout(cancel_row)

        body.addSpacing(6)

        self._countdown_lbl = QLabel()
        self._countdown_lbl.setObjectName("stateCountdown")
        self._countdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self._countdown_lbl)

        body.addStretch(2)
        layout.addLayout(body, stretch=1)

        self._remaining = IDLE_SECONDS
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._tick)
        self._buttons: list[QPushButton] = []

    def enter(self, *, name: str = "Faculty", cabinets: list[dict] | None = None, **_ctx) -> None:
        cabinets = cabinets or []
        self._greeting.setText(f"Welcome, {name}")
        self._build_cabinet_buttons(cabinets)
        self._remaining = IDLE_SECONDS
        self._refresh_countdown()
        self._idle_timer.start(1000)

    def leave(self) -> None:
        self._idle_timer.stop()
        self._clear_buttons()

    def _build_cabinet_buttons(self, cabinets: list[dict]) -> None:
        self._clear_buttons()
        for cab in cabinets:
            cab_id = cab["id"]
            label = f"Cabinet {cab_id}"
            btn = QPushButton(label)
            btn.setObjectName("cabinetSelectButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, c=cab_id: self._on_cabinet_clicked(c))
            self._btn_row.insertWidget(self._btn_row.count(), btn)
            self._buttons.append(btn)
        self._btn_row.addStretch(1)

    def _clear_buttons(self) -> None:
        for btn in self._buttons:
            self._btn_row.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()
        while self._btn_row.count() > 1:
            item = self._btn_row.takeAt(self._btn_row.count() - 1)
            if item:
                del item

    def _on_cabinet_clicked(self, cabinet_id: str) -> None:
        self._idle_timer.stop()
        self.cabinet_selected.emit(cabinet_id)

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self._idle_timer.stop()
            self.cancel_requested.emit()
            return
        self._refresh_countdown()

    def _refresh_countdown(self) -> None:
        self._countdown_lbl.setText(f"Auto-cancel in {self._remaining}s")
