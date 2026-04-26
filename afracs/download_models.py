"""Download YuNet and SFace ONNX models: python -m afracs.download_models"""
import sys
import urllib.request
from pathlib import Path

from afracs import config

_BASE = "https://github.com/opencv/opencv_zoo/raw/main/models"

_MODELS = [
    (
        f"{_BASE}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        config.FACE_DETECTOR_MODEL,
        400_000,
    ),
    (
        f"{_BASE}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        config.FACE_RECOGNIZER_MODEL,
        30_000_000,
    ),
]


def _progress(block_num: int, block_size: int, total_size: int) -> None:
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded * 100 / total_size, 100)
        bar = "#" * int(pct / 2)
        print(f"\r  [{bar:<50}] {pct:5.1f}%", end="", flush=True)


def download_all() -> None:
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for url, dest, min_size in _MODELS:
        dest = Path(dest)
        if dest.exists() and dest.stat().st_size >= min_size:
            print(f"  {dest.name} — already present, skipping.")
            continue

        print(f"\nDownloading {dest.name} …")
        try:
            urllib.request.urlretrieve(url, dest, reporthook=_progress)
            print(f"\n  Saved to {dest}")
        except Exception as exc:
            print(f"\n  ERROR: {exc}", file=sys.stderr)
            if dest.exists():
                dest.unlink()
            sys.exit(1)


if __name__ == "__main__":
    print("AFRACS — model downloader")
    download_all()
    print("\nAll models ready.")
