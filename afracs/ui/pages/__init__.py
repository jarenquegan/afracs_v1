"""Per-state page widgets."""

from afracs.ui.pages.alert_page import AlertPage
from afracs.ui.pages.denied_page import DeniedPage
from afracs.ui.pages.detecting_page import DetectingPage
from afracs.ui.pages.granted_page import GrantedPage
from afracs.ui.pages.selecting_page import SelectingPage
from afracs.ui.pages.sleep_page import SleepPage

__all__ = [
    "AlertPage",
    "DeniedPage",
    "DetectingPage",
    "GrantedPage",
    "SelectingPage",
    "SleepPage",
]
