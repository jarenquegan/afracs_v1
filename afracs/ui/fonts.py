"""Font registration and helpers."""

from PyQt6.QtGui import QFont, QFontDatabase

from afracs import config, theme


def install_fonts() -> str:
    """Register all TTF/OTF files from assets/fonts/ with Qt.

    Returns the family name of the first registered Geist font,
    or empty string if none found.
    """
    fonts_dir = config.ASSETS_DIR / "fonts"
    if not fonts_dir.exists():
        return ""

    geist_family = ""
    for path in sorted(fonts_dir.iterdir()):
        if path.suffix.lower() in {".ttf", ".otf"}:
            fid = QFontDatabase.addApplicationFont(str(path))
            if fid != -1 and not geist_family:
                families = QFontDatabase.applicationFontFamilies(fid)
                if families and "geist" in families[0].lower():
                    geist_family = families[0]

    return geist_family or ""


def base_font(point_size: int = 11, weight: int = theme.FontWeight.REGULAR) -> QFont:
    font = QFont(theme.FONT_FAMILY, point_size)
    font.setWeight(QFont.Weight(weight))
    return font
