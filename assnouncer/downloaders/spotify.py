from __future__ import annotations

import asyncio

from assnouncer.config import FFMPEG_PATH
from assnouncer.asspp import Timestamp
from assnouncer.downloaders.base import BaseDownloader

from typing import List, ClassVar
from pathlib import Path


class SpotifyDownloader(BaseDownloader):
    PATTERNS: ClassVar[List[str]] = [
        r"https://(www\.)?open\.spotify\.com/track/.*",
    ]

    @staticmethod
    async def download(url: str, filename: Path, start: Timestamp = None, stop: Timestamp = None) -> bool:
        cmd = (
            f"spotdl "
            f"-f {FFMPEG_PATH} "
            f"-p {filename} "
            f"--output-format opus "
            f"{url}"
        )

        process = await asyncio.create_subprocess_shell(cmd)
        if await process.wait() != 0:
            return False

        if not BaseDownloader.cut(filename, start=start, stop=stop):
            filename.unlink()
            return False

        return True
