import subprocess
import urllib.request
import re

from config import FFMPEG_DIR

from metaclass import Descriptor
from typing import List
from pathlib import Path


class BaseDownloader(metaclass=Descriptor):
    PATTERNS: List[str] = None

    @classmethod
    def validate(cls):
        if cls == BaseDownloader:
            return

        msg = "PATTERNS must be a non-empty list of str"
        assert cls.PATTERNS, msg
        assert isinstance(cls.PATTERNS, list), msg
        assert all(isinstance(k, str) for k in cls.PATTERNS), msg

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
        r"https://(www\.)?soundcloud\.com/.*",
        r"https://(www\.)?open\.spotify\.com/track/.*",
        # TODO(daniel): Dailymotion download takes ages
        #   r"https://(www\.)?dailymotion\.com/video/.*",
        r"https://(www\.)?vimeo\.com/.*"
    ]

    @staticmethod
    def download(url: str, filename: Path) -> bool:
        return subprocess.run(
            f"yt-dlp "
            f"-x "
            f"-i "
            f"-f ba "
            f"-o {filename.with_suffix('')}.%(ext)s "
            f"--http-chunk-size 10M "
            f"--buffer-size 32K "
            f"--audio-format vorbis "
            f"--audio-quality 160K "
            f"--ffmpeg-location {FFMPEG_DIR} "
            f"{url}"
        ).returncode == 0


# TODO(daniel): Verify that the url points to something playable
#
# class DirectDownloader(BaseDownloader):
#     PATTERNS: List[str] = [
#         r"https?://(www\.).*"
#     ]
#
#     @staticmethod
#     def download(url: str, filename: Path) -> bool:
#         return urllib.request.urlretrieve(url, str(filename))
