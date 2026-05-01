"""Persistent header strip."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from afracs import config, theme
from afracs.ui.typing_label import TypingLabel

LOGO_SIZE = 44


def _logo(filename: str) -> QLabel:
    label = QLabel()
    pix = QPixmap(str(config.ASSETS_DIR / filename))
    label.setPixmap(
        pix.scaled(
            LOGO_SIZE,
            LOGO_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )
    label.setFixedSize(LOGO_SIZE, LOGO_SIZE)
    return label


class HeaderBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("headerBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(16)

        layout.addWidget(_logo("ucv_logo.png"))

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

        layout.addWidget(_logo("afracs_logo.png"))

        # Lock header height so the sleep page body always gets the same available height.
        # Without this, TypingLabel text changes cause the header to breathe ±1px,
        # which shifts stretch distribution and makes the clock visibly jump in size.
        _text_h = theme.FontSize.HEADER_TITLE + 4 + theme.FontSize.HEADER_SUBTITLE
        self.setFixedHeight(20 + max(LOGO_SIZE, _text_h))
