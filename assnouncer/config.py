from __future__ import annotations

import os
import sys

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

if sys.platform == "win32":
    FFMPEG_DIR = Path(env("FFMPEG_DIR", "C:/Users/Admin/Documents/Applications/"))
    FFMPEG_PATH = FFMPEG_DIR / "ffmpeg.exe"
    FFPROBE_PATH = FFMPEG_DIR / "ffprobe.exe"
else:
    FFMPEG_DIR = ""
    FFMPEG_PATH = "ffmpeg"
    FFPROBE_PATH = "ffprobe"

GUILD_ID = 642747343208185857
