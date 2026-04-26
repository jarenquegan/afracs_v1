"""QSS stylesheet for the cabinet window."""

from afracs import theme

T = theme
FW = theme.FontWeight
FS = theme.FontSize
SP = theme.Space
R = theme.Radius

CABINET_QSS = f"""
* {{
    font-family: {T.FONT_STACK};
}}

QWidget#root {{
    background: {T.MAROON_DARKEST};
}}

/* Header bar */
QWidget#headerBar {{
    background: {T.MAROON_DARK};
    border-bottom: 1px solid {T.GOLD_DARK};
}}
QLabel#headerTitle {{
    color: {T.GOLD};
    font-size: {FS.HEADER_TITLE}px;
    font-weight: {FW.BOLD};
    letter-spacing: 1px;
}}
QLabel#headerSubtitle {{
    color: white;
    font-size: {FS.HEADER_SUBTITLE}px;
    font-weight: {FW.REGULAR};
    letter-spacing: 0.4px;
}}

/* SLEEP page */
QWidget#sleepPage {{
    background: {T.MAROON_DARKEST};
}}
QLabel#sleepClock {{
    color: {T.GOLD};
    font-size: {FS.LOCK_CLOCK}px;
    font-weight: {FW.BOLD};
    letter-spacing: 4px;
}}
QLabel#sleepDate {{
    color: white;
    font-size: {FS.LOCK_DATE}px;
    font-weight: {FW.LIGHT};
    letter-spacing: 1px;
}}
QPushButton#sleepWakeButton {{
    background: {T.GOLD};
    color: {T.MAROON_DARKEST};
    font-size: {FS.BUTTON}px;
    font-weight: {FW.SEMIBOLD};
    padding: 14px 44px;
    border: none;
    border-radius: {R.PILL}px;
    letter-spacing: 2px;
}}
QPushButton#sleepWakeButton:hover {{
    background: {T.GOLD_DARK};
}}
QPushButton#sleepWakeButton:pressed {{
    background: {T.GOLD_DARK};
    padding-top: 16px;
    padding-bottom: 12px;
}}
QLabel#statusDot {{
    color: {T.GOLD_DARK};
    font-size: {FS.STATUS_DOT}px;
    font-weight: {FW.REGULAR};
    letter-spacing: 0.6px;
    padding: 0 {SP.SM}px {SP.MD}px {SP.SM}px;
    background: transparent;
}}
QPushButton#adminButton {{
    background: transparent;
    color: rgba(255,255,255,0.30);
    font-size: 11px;
    font-weight: {FW.REGULAR};
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 4px;
    padding: 3px 10px;
    letter-spacing: 0.5px;
}}
QPushButton#adminButton:hover {{
    color: {T.GOLD};
    border-color: {T.GOLD_DARK};
    background: rgba(255,255,255,0.05);
}}

/* DETECTING page */
QLabel#cameraView {{
    background: black;
    color: {T.GOLD};
    font-size: {FS.BANNER}px;
    margin: {SP.MD}px;
    border-radius: {R.LG}px;
    border: 1px solid {T.SURFACE_DIM};
}}

/* GRANTED / DENIED / ALERT body */
QLabel#bigGlyph {{
    font-size: {FS.BIG_GLYPH}px;
    font-weight: {FW.BOLD};
}}
QLabel#bigGlyph[state="granted"] {{ color: {T.SUCCESS_GREEN}; }}
QLabel#bigGlyph[state="denied"]  {{ color: {T.DANGER_RED}; }}
QLabel#bigGlyph[state="alert"]   {{ color: {T.GOLD}; }}

QLabel#stateTitle {{
    color: white;
    font-size: {FS.STATE_TITLE}px;
    font-weight: {FW.BOLD};
    letter-spacing: 0.5px;
}}
QLabel#stateBody {{
    color: white;
    font-size: {FS.STATE_BODY}px;
    font-weight: {FW.REGULAR};
    letter-spacing: 0.3px;
}}
QLabel#stateMeta {{
    color: {T.GOLD};
    font-size: {FS.STATE_META}px;
    font-weight: {FW.SEMIBOLD};
}}
QLabel#stateCountdown {{
    color: rgba(255, 255, 255, 0.55);
    font-size: {FS.STATE_META}px;
    font-weight: {FW.LIGHT};
    letter-spacing: 0.3px;
}}
QPushButton#retryButton {{
    background: transparent;
    color: {T.GOLD};
    font-size: {FS.BUTTON}px;
    font-weight: {FW.SEMIBOLD};
    padding: 10px 36px;
    border: 1px solid {T.GOLD_DARK};
    border-radius: {R.PILL}px;
    letter-spacing: 1px;
}}
QPushButton#retryButton:hover {{
    background: {T.GOLD_DARK};
    color: {T.MAROON_DARKEST};
    border-color: {T.GOLD};
}}
QPushButton#retryButton:pressed {{
    background: {T.GOLD};
    color: {T.MAROON_DARKEST};
}}

/* SELECTING page */
QWidget#selectingPage {{
    background: {T.MAROON_DARKEST};
}}
QPushButton#cabinetSelectButton {{
    background: transparent;
    color: {T.GOLD};
    font-size: {FS.BUTTON}px;
    font-weight: {FW.SEMIBOLD};
    padding: 10px 32px;
    border: 1px solid {T.GOLD_DARK};
    border-radius: {R.PILL}px;
    letter-spacing: 1px;
    min-width: 110px;
}}
QPushButton#cabinetSelectButton:hover {{
    background: {T.GOLD_DARK};
    color: {T.MAROON_DARKEST};
    border-color: {T.GOLD};
}}
QPushButton#cabinetSelectButton:pressed {{
    background: {T.GOLD};
    color: {T.MAROON_DARKEST};
    border-color: {T.GOLD};
}}
QPushButton#cancelButton {{
    background: transparent;
    color: rgba(255,255,255,0.45);
    font-size: {FS.STATE_META}px;
    font-weight: {FW.REGULAR};
    padding: 6px 20px;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: {R.PILL}px;
    letter-spacing: 0.5px;
}}
QPushButton#cancelButton:hover {{
    color: white;
    border-color: rgba(255,255,255,0.40);
}}

/* Bottom status bar */
QFrame#statusBarBorder {{
    background: {T.GOLD};
    border: none;
}}
QWidget#statusBar {{
    background: {T.MAROON_DARK};
}}
QLabel#statusBarInfo {{
    color: white;
    font-size: {FS.STATUS_BAR}px;
    font-weight: {FW.REGULAR};
    letter-spacing: 0.4px;
}}
QLabel#statusBarSep {{
    color: {T.GOLD_DARK};
    font-size: {FS.STATUS_BAR}px;
    padding: 0 12px;
}}
QLabel#statusBarTip {{
    color: {T.GOLD};
    font-size: {FS.STATUS_BAR}px;
    font-weight: {FW.LIGHT};
    font-style: italic;
    letter-spacing: 0.3px;
}}
QLabel#statusBarDateTime {{
    color: {T.GOLD};
    font-size: {FS.STATUS_BAR}px;
    font-weight: {FW.SEMIBOLD};
    letter-spacing: 0.5px;
}}
"""
