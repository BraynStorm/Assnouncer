import subprocess
import regex

from config import FFMPEG_DIR

from commandline import Timestamp
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
        return any(regex.fullmatch(pattern, url) is not None for pattern in cls.PATTERNS)

    @staticmethod
    def download(
        uri: str,
        filename: Path,
        start: Timestamp = None,
        stop: Timestamp = None
    ) -> bool:
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
    def download(
        url: str,
        filename: Path,
        start: Timestamp = None,
        stop: Timestamp = None
    ) -> bool:
        filename_ogg = filename.with_suffix(".ogg")
        filename_tmp = filename.with_suffix(".tmp.ogg")
        filename_ns = filename.with_suffix("")

        cmd = (
            f"yt-dlp "
            f"-x "
            f"-i "
            f"-f ba "
            f"-o {filename_ns}.%(ext)s "
            f"--http-chunk-size 10M "
            f"--buffer-size 32K "
            f"--audio-format vorbis "
            f"--audio-quality 0 "
            f"--ffmpeg-location {FFMPEG_DIR} "
            f"{url}"
        )

        if subprocess.run(cmd).returncode != 0:
            return False

        if start is None and stop is None:
            return True

        if None not in (start, stop) and start.value > stop.value:
            return False

        cmd = f"{FFMPEG_DIR}/ffmpeg.exe -hide_banner -loglevel error"

        if start is not None:
            cmd = f"{cmd} -ss {start.value}"

        if stop is not None:
            cmd = f"{cmd} -to {stop.value}"

        cmd = f"{cmd} -i {filename_ogg} -c copy {filename_tmp}"
        if subprocess.run(cmd).returncode != 0:
            filename_ogg.unlink()
            filename_tmp.unlink()
            return False

        filename_ogg.unlink()
        filename_tmp.rename(filename_ogg)

        return True


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
