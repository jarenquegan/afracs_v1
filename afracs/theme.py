"""Brand palette, typography, and spacing tokens."""

MAROON_DARKEST = "#350200"
MAROON_DARK    = "#6C0200"
MAROON         = "#900500"
GOLD_DARK      = "#BD953E"
GOLD           = "#D4B356"

SUCCESS_GREEN   = "#1B7F3A"
DANGER_RED      = "#B00020"
DANGER_RED_DARK = "#7A0016"
SURFACE_DIM     = "#2A0100"

FONT_FAMILY    = "Geist"
FONT_FALLBACKS = "'Helvetica Neue', Helvetica, 'DejaVu Sans', Arial, sans-serif"
FONT_STACK     = f"'{FONT_FAMILY}', {FONT_FALLBACKS}"


class FontSize:
    LOCK_CLOCK      = 132
    LOCK_DATE       = 22
    HEADER_TITLE    = 22
    HEADER_SUBTITLE = 13
    HEADER_CLOCK    = 22
    BANNER          = 20
    BIG_GLYPH       = 132
    STATE_TITLE     = 38
    STATE_BODY      = 18
    STATE_META      = 16
    BUTTON          = 15
    STATUS_DOT      = 12
    STATUS_BAR      = 11


class FontWeight:
    LIGHT     = 300
    REGULAR   = 400
    SEMIBOLD  = 600
    BOLD      = 700


class Space:
    XS = 6
    SM = 12
    MD = 18
    LG = 28
    XL = 44


class Radius:
    SM = 6
    MD = 10
    LG = 16
    PILL = 28


_rescaled = False


def rescale(factor: float) -> None:
    """Scale all size/spacing tokens by factor. Call once before building QSS."""
    global _rescaled
    if _rescaled:
        return
    _rescaled = True
    factor = max(0.4, min(factor, 3.0))
    for cls in (FontSize, Space, Radius):
        for attr in list(vars(cls)):
            if not attr.startswith("_") and isinstance(getattr(cls, attr), (int, float)):
                setattr(cls, attr, max(1, round(getattr(cls, attr) * factor)))
