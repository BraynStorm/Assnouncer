import subprocess
import regex

from assnouncer.config import FFMPEG_PATH
from assnouncer.asspp import Timestamp, Number, Null
from assnouncer.metaclass import Descriptor

from typing import List, Union
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
        start: Union[Timestamp, Number] = Null,
        stop: Union[Timestamp, Number] = Null
    ) -> bool:
        pass

    @staticmethod
    def cut(
        filename: Path,
        start: Union[Timestamp, Number] = Null,
        stop: Union[Timestamp, Number] = Null
    ) -> bool:
        if Null not in (start, stop) and start >= stop:
            print(f"[warn] Incorrect timestamp: {start} >= {stop}")
            return False

        if start == Null and stop == Null:
            return True

        filename_tmp = filename.with_suffix(".tmp.opus")

        cmd = f"{FFMPEG_PATH} -hide_banner -loglevel error"

        if start != Null:
            cmd = f"{cmd} -ss {start.value}"

        if stop != Null:
            cmd = f"{cmd} -to {stop.value}"

        cmd = f"{cmd} -i {filename} -c copy {filename_tmp}"
        if subprocess.run(cmd).returncode != 0:
            filename_tmp.unlink()
            return False

        filename.unlink()
        filename_tmp.rename(filename)

        return True