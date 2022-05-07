from __future__ import annotations

from assnouncer import util
from assnouncer.asspp import String, Timestamp
from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, ClassVar


@dataclass
class Download(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["download", "dl"]

    async def on_command(self, payload: String, start: Timestamp = None, stop: Timestamp = None):
        """
        Download a song to the cache

        :param payload: Url or Youtube query for the song.
        :param start: (Optional) Start timestamp within the song.
        :param stop: (Optional) End timestamp within the song.
        """
        await util.download(payload, start=start, stop=stop, force=True)
