from __future__ import annotations

import asyncio

from assnouncer.config import FFMPEG_DIR
from assnouncer.asspp import Timestamp
from assnouncer.downloaders.base import BaseDownloader

from dataclasses import dataclass
from typing import List, ClassVar
from pathlib import Path


@dataclass
class FallbackDownloader(BaseDownloader):
    PATTERNS: ClassVar[List[str]] = [
        r"https://.*.(wav|mp3|mp4|opus|ogg|m4a)",
        r"https://youtu.be/.*",
        r"https://cdn\.discordapp\.com/attachments/[0-9]+/[0-9]+/.*\.(wav|mp3|mp4|opus|ogg|m4a)",
        r"https://(www\.)?youtube\.com/watch\?v=.*",
        r"https://(www\.)?soundcloud\.com/.*",
        # TODO(daniel): Dailymotion download takes ages
        #   r"https://(www\.)?dailymotion\.com/video/.*",
        r"https://(www\.)?vimeo\.com/.*",
        r"https://(www\.)?streamable.com/.*",
    ]

    @staticmethod
    async def download(url: str, filename: Path, start: Timestamp = None, stop: Timestamp = None) -> bool:
        filename_ns = filename.with_suffix("")

        cmd = (
            f"yt-dlp "
            f"-x "
            f"-i "
            # f"-f ba "
            f"-o {filename_ns}.%(ext)s "
            f"--http-chunk-size 10M "
            f"--buffer-size 32K "
            f"--audio-format opus "
            f"--audio-quality 0 "
            f"--ffmpeg-location {FFMPEG_DIR} "
            f"{url}"
        )

        process = await asyncio.create_subprocess_shell(cmd)
        if await process.wait() != 0:
            return False

        if not await BaseDownloader.cut(filename, start=start, stop=stop):
            filename.unlink()
            return False

        return True
