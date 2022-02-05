from __future__ import annotations

import hashlib

from config import THEMES_DIR, FFMPEG_PATH, DOWNLOAD_DIR

from pathlib import Path
from typing import Union
from discord import FFmpegOpusAudio


def get_theme_path(user: str) -> Path:
    return (THEMES_DIR / user).with_suffix(".ogg")


def get_download_path(uri: str) -> Path:
    hash_value = hashlib.md5(uri.encode("utf8")).hexdigest()
    return (DOWNLOAD_DIR / hash_value).with_suffix(".ogg")


async def load_source(uri: Union[Path, str]) -> FFmpegOpusAudio:
    return await FFmpegOpusAudio.from_probe(
        source=str(uri),
        executable=str(FFMPEG_PATH)
    )
