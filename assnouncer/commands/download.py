from __future__ import annotations

from assnouncer import util
from assnouncer.asspp import String, Timestamp, Number, Null
from assnouncer.commands.base import BaseCommand

from typing import List, Union


class Download(BaseCommand):
    ALIASES: List[str] = ["download", "dl"]

    async def on_command(
        self,
        payload: String,
        start: Union[Timestamp, Number] = Null,
        stop: Union[Timestamp, Number] = Null
    ):
        """
        Download a song to the cache

        :param payload: Url or Youtube query for the song.
        :param start: (Optional) Start timestamp within the song.
        :param stop: (Optional) End timestamp within the song.
        """
        await util.download(payload.value, start=start, stop=stop, force=True)
