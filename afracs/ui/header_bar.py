"""Persistent header strip."""

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from afracs import config
from afracs.ui.typing_label import TypingLabel

LOGO_SIZE = 44


class ClickableLogo(QLabel):
    clicked = pyqtSignal()

    def __init__(self, filename: str, parent=None):
        super().__init__(parent)
        pix = QPixmap(str(config.ASSETS_DIR / filename))
        self.setPixmap(
            pix.scaled(
                LOGO_SIZE,
                LOGO_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.setFixedSize(LOGO_SIZE, LOGO_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class HeaderBar(QWidget):
    exit_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("headerBar")

        self._tap_count = 0
        self._tap_timer = QTimer(self)
        self._tap_timer.setSingleShot(True)
        self._tap_timer.timeout.connect(self._reset_taps)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(16)

        self.logo = ClickableLogo("ucv_logo.png")
        self.logo.clicked.connect(self._on_logo_clicked)
        layout.addWidget(self.logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("University of Cagayan Valley")
        title.setObjectName("headerTitle")
        title_box.addWidget(title)

        subtitle = TypingLabel(
            [
                "AFRACS · Equipment Cabinet",
                "College of Health · Equipment Cabinet",
            ]
        )
        subtitle.setObjectName("headerSubtitle")
        subtitle.setMinimumWidth(420)
        title_box.addWidget(subtitle)

        layout.addLayout(title_box, stretch=1)

        layout.addWidget(ClickableLogo("afracs_logo.png"))

    def _on_logo_clicked(self) -> None:
        self._tap_count += 1
        self._tap_timer.start(1000)  # 1 second window
        if self._tap_count >= 3:
            self.exit_requested.emit()

    def _reset_taps(self) -> None:
        self._tap_count = 0

