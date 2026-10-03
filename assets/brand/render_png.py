"""Render the brand SVGs to PNG with a headless Chromium browser (Edge or Chrome).

Transparent PNGs are recovered exactly from two renders, on black and on white.
Needs Pillow and numpy (both come with the project's dev environment through matplotlib).

Run from the repository root:  python assets/brand/render_png.py [path/to/browser]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "msedge",
    "google-chrome",
    "chromium",
]

# name, source svg, css width, css height, device scale, transparent background
JOBS = [
    ("logo.png", "logo-light.svg", 0, 64, 3, True),
    ("logo-dark.png", "logo-dark.svg", 0, 64, 3, True),
    ("logo-mark.png", "logo-mark.svg", 64, 64, 8, True),
    ("banner.png", "banner.svg", 1280, 320, 2, True),
    ("social-preview.png", "social-preview.svg", 1280, 640, 1, False),
]


def browser(arg: str | None) -> str:
    for c in [arg, *CANDIDATES]:
        if c and (Path(c).exists() or shutil.which(c)):
            return c
    raise SystemExit("no Edge or Chrome found; pass the browser path as the first argument")


def shot(exe: str, src: Path, out: Path, w: int, h: int, scale: float, bg: str) -> None:
    out.unlink(missing_ok=True)
    args = [
        exe,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={w},{h}",
        f"--force-device-scale-factor={scale}",
        f"--default-background-color={bg}",
        f"--screenshot={out}",
        src.as_uri(),
    ]
    subprocess.run(args, capture_output=True, timeout=120, check=False)
    for _ in range(200):  # the browser can return before the file is flushed
        if out.exists() and out.stat().st_size > 0:
            time.sleep(0.2)
            return
        time.sleep(0.1)
    raise SystemExit(f"no screenshot written for {src.name}")


def svg_width(src: Path) -> int:
    head = src.read_text(encoding="utf-8")[:300]
    return round(float(head.split('width="', 1)[1].split('"', 1)[0]))


def render(exe: str, name: str, src: Path, w: int, h: int, scale: float, clear: bool) -> None:
    import numpy as np
    from PIL import Image

    w = w or svg_width(src)
    out = HERE / name
    with tempfile.TemporaryDirectory() as tmp:
        on_white, on_black = Path(tmp) / "w.png", Path(tmp) / "b.png"
        shot(exe, src, on_white, w, h, scale, "FFFFFFFF")
        if not clear:
            Image.open(on_white).convert("RGB").save(out, optimize=True)
            return
        shot(exe, src, on_black, w, h, scale, "000000FF")
        white = np.asarray(Image.open(on_white).convert("RGB"), dtype=float)
        black = np.asarray(Image.open(on_black).convert("RGB"), dtype=float)
    alpha = np.clip(1.0 - (white - black).mean(axis=2) / 255.0, 0.0, 1.0)
    safe = np.where(alpha > 1e-4, alpha, 1.0)[..., None]
    rgb = np.clip(black / safe, 0, 255)
    rgba = np.dstack([rgb, alpha * 255]).round().astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(out, optimize=True)


def main() -> None:
    exe = browser(sys.argv[1] if len(sys.argv) > 1 else None)
    for name, src, w, h, scale, clear in JOBS:
        render(exe, name, HERE / src, w, h, scale, clear)
        print(f"wrote {HERE / name}")


if __name__ == "__main__":
    main()
