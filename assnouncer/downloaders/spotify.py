from __future__ import annotations

import subprocess

from assnouncer.config import FFMPEG_PATH
from assnouncer.asspp import Null, Number, Timestamp
from assnouncer.downloaders.base import BaseDownloader

from typing import List, Union
from pathlib import Path


class SpotifyDownloader(BaseDownloader):
    PATTERNS: List[str] = [
        r"https://(www\.)?open\.spotify\.com/track/.*",
    ]

    @staticmethod
    def download(
        url: str,
        filename: Path,
        start: Union[Timestamp, Number] = Null,
        stop: Union[Timestamp, Number] = Null
    ) -> bool:
        cmd = (
            f"spotdl "
            f"-f {FFMPEG_PATH} "
            f"-p {filename} "
            f"--output-format opus "
            f"{url}"
        )

        if subprocess.run(cmd).returncode != 0:
            return False

        if not BaseDownloader.cut(filename, start=start, stop=stop):
            filename.unlink()
            return False

        return True