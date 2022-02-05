from __future__ import annotations

import os

from pathlib import Path
from typing import Any


def env(k: str, d: Any = None):
    return os.environ.get(k, d)


HERE = Path(".")

DOWNLOAD_DIR = HERE / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

THEMES_DIR = HERE / "themes"
THEMES_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_PATH = HERE / "token"

FFMPEG_DIR = Path(env("FFMPEG_DIR", "C:/Users/Admin/Documents/Applications/"))
FFMPEG_PATH = FFMPEG_DIR / "ffmpeg.exe"
