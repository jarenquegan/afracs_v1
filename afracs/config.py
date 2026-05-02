"""Project settings loaded from .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "afracs" / "ui" / "assets"
MODELS_DIR = PROJECT_ROOT / "models"

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

CABINET_NAME = os.getenv("CABINET_NAME", "Cabinet")

GPIO_LOCK_PIN = int(os.getenv("GPIO_LOCK_PIN", "17"))
GPIO_BUZZER_PIN = int(os.getenv("GPIO_BUZZER_PIN", "24"))
BUZZER_FREQUENCY = int(os.getenv("BUZZER_FREQUENCY", "2500"))
LOCK_PULSE_SECONDS = float(os.getenv("LOCK_PULSE_SECONDS", "7.5"))

ALERT_AFTER_FAILED_ATTEMPTS = int(os.getenv("ALERT_AFTER_FAILED_ATTEMPTS", "5"))

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "afracs")

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "@L01e1t1")


def _parse_lock_pins(raw: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            cab_id, pin = pair.split(":", 1)
            try:
                result[cab_id.strip()] = int(pin.strip())
            except ValueError:
                pass
    return result


CABINET_LOCK_PINS: dict[str, int] = _parse_lock_pins(
    os.getenv("CABINET_LOCK_PINS", "")
)
FACE_DETECTOR_MODEL = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
FACE_RECOGNIZER_MODEL = MODELS_DIR / "face_recognition_sface_2021dec.onnx"
# SFace paper baseline cosine threshold.
RECOGNITION_THRESHOLD = float(os.getenv("RECOGNITION_THRESHOLD", "0.363"))
RECOGNITION_STREAK = int(os.getenv("RECOGNITION_STREAK", "5"))
UNRECOGNISED_DENY_FRAMES = int(os.getenv("UNRECOGNISED_DENY_FRAMES", "90"))
ENROLL_SAMPLES = int(os.getenv("ENROLL_SAMPLES", "30"))
