from __future__ import annotations

import logging
import asyncio
import regex

from assnouncer.config import FFMPEG_PATH
from assnouncer.asspp import Timestamp
from assnouncer.metaclass import Descriptor

from dataclasses import dataclass
from typing import List, ClassVar
from pathlib import Path


logger = logging.getLogger(__name__)

@dataclass
class BaseDownloader(metaclass=Descriptor):
    PATTERNS: ClassVar[List[str]] = []

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
    async def download(uri: str, filename: Path, start: Timestamp = None, stop: Timestamp = None) -> bool:
        pass

    @staticmethod
    async def cut(filename: Path, start: Timestamp = None, stop: Timestamp = None) -> bool:
        if None not in (start, stop) and start >= stop:
            logger.warn(f"Incorrect timestamp: {start} >= {stop}")
            return False

        if start is None and stop is None:
            return True

        filename_tmp = filename.with_suffix(".tmp.opus")

        cmd = f"{FFMPEG_PATH} -hide_banner -loglevel error"

        if start is not None:
            cmd = f"{cmd} -ss {start.value}"

        if stop is not None:
            cmd = f"{cmd} -to {stop.value}"

        cmd = f"{cmd} -i {filename} -c copy {filename_tmp}"
        process = await asyncio.create_subprocess_shell(cmd)
        if await process.wait() != 0:
            filename_tmp.unlink()
            return False

        filename.unlink()
        filename_tmp.rename(filename)

        return True
