"""Download Geist font TTF files: python -m afracs.download_fonts"""
import sys
import urllib.request
from pathlib import Path

from afracs import config

FONTS_DIR = config.ASSETS_DIR / "fonts"

_BASE = "https://raw.githubusercontent.com/vercel/geist-font/main/packages/next/dist/fonts/geist-sans"

_FONTS = [
    "Geist-Light.ttf",
    "Geist-Regular.ttf",
    "Geist-Medium.ttf",
    "Geist-SemiBold.ttf",
    "Geist-Bold.ttf",
]

_MIN_SIZE = 50_000


def download_geist() -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    all_present = all(
        (FONTS_DIR / name).exists() and (FONTS_DIR / name).stat().st_size >= _MIN_SIZE
        for name in _FONTS
    )
    if all_present:
        print("  Geist fonts already present, skipping.")
        return

    for name in _FONTS:
        dest = FONTS_DIR / name
        if dest.exists() and dest.stat().st_size >= _MIN_SIZE:
            print(f"  {name} — already present, skipping.")
            continue

        url = f"{_BASE}/{name}"
        print(f"  Downloading {name}...")
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"    Saved ({dest.stat().st_size:,} bytes)")
        except Exception as exc:
            print(f"    ERROR: {exc}", file=sys.stderr)
            if dest.exists():
                dest.unlink()
            sys.exit(1)


if __name__ == "__main__":
    print("AFRACS — font downloader")
    download_geist()
    print("Done.")
