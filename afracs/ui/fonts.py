"""Font helpers."""

from PyQt6.QtGui import QFont

from afracs import theme


def install_fonts() -> str:
    return ""


def base_font(point_size: int = 11, weight: int = theme.FontWeight.REGULAR) -> QFont:
    font = QFont(theme.FONT_FAMILY, point_size)
    font.setWeight(QFont.Weight(weight))
    return font
