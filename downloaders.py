import subprocess
import urllib.request
import re

from config import FFMPEG_DIR

from metaclass import Descriptor
from typing import List
from pathlib import Path
from sclib import SoundcloudAPI


class BaseDownloader(metaclass=Descriptor):
    PATTERNS: List[str] = None

    @classmethod
    def accept(cls, url: str) -> bool:
        return any(re.fullmatch(pattern, url) is not None for pattern in cls.PATTERNS)

    @staticmethod
    def download(uri: str, filename: Path) -> bool:
        pass


class FallbackDownloader(BaseDownloader):
    PATTERNS: List[str] = [
        r"https://youtu.be/.*",
        r"https://(www\.)?youtube\.com/watch\?v=.*",
        r"https://(www\.)?soundcloud\.com/.*"
    ]

    @staticmethod
    def download(url: str, filename: Path) -> bool:
        return subprocess.run(
            f"yt-dlp "
            f"-f ba "
            f"--ignore-errors "
            f"--extract-audio "
            f"--audio-format vorbis "
            f"--audio-quality 160K "
            f"--output {filename.with_suffix('')}.%(ext)s "
            f"--ffmpeg-location {FFMPEG_DIR} "
            f"{url}"
        ).returncode == 0


class DirectDownloader(BaseDownloader):
    PATTERNS: List[str] = [
        r"https?://(www\.).*"
    ]

    @staticmethod
    def download(url: str, filename: Path) -> bool:
        return urllib.request.urlretrieve(url, str(filename))