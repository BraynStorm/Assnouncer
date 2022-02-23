from __future__ import annotations

import subprocess

from assnouncer.config import FFMPEG_DIR
from assnouncer.asspp import Null, Number, Timestamp
from assnouncer.downloaders.base import BaseDownloader

from typing import List, Union
from pathlib import Path


class FallbackDownloader(BaseDownloader):
    PATTERNS: List[str] = [
        r"https://youtu.be/.*",
        r"https://cdn\.discordapp\.com/attachments/[0-9]+/[0-9]+/.*\.(wav|mp3|opus|ogg|m4a)",
        r"https://(www\.)?youtube\.com/watch\?v=.*",
        r"https://(www\.)?soundcloud\.com/.*",
        # TODO(daniel): Dailymotion download takes ages
        #   r"https://(www\.)?dailymotion\.com/video/.*",
        r"https://(www\.)?vimeo\.com/.*"
    ]

    @staticmethod
    def download(
        url: str,
        filename: Path,
        start: Union[Timestamp, Number] = Null,
        stop: Union[Timestamp, Number] = Null
    ) -> bool:
        filename_ns = filename.with_suffix("")

        cmd = (
            f"yt-dlp "
            f"-x "
            f"-i "
            f"-f ba "
            f"-o {filename_ns}.%(ext)s "
            f"--http-chunk-size 10M "
            f"--buffer-size 32K "
            f"--audio-format opus "
            f"--audio-quality 0 "
            f"--ffmpeg-location {FFMPEG_DIR} "
            f"{url}"
        )

        if subprocess.run(cmd).returncode != 0:
            return False

        if not BaseDownloader.cut(filename, start=start, stop=stop):
            filename.unlink()
            return False

        return True
