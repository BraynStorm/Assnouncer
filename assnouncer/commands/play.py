from __future__ import annotations

from assnouncer import util
from assnouncer.asspp import String, Timestamp
from assnouncer.commands.base import BaseCommand

from typing import List, ClassVar


class Play(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["play", "плаъ", "πλαυ", "playing"]

    async def on_command(self, payload: String, start: Timestamp = None, stop: Timestamp = None):
        """
        Add a song to Assnouncer's queue.

        :param payload: Url or Youtube query for the song.
        :param start: (Optional) Start timestamp within the song.
        :param stop: (Optional) End timestamp within the song.
        """
        request = await util.download(payload.value, start=start, stop=stop)
        if request is None:
            uri = util.resolve_uri(payload.value)
            print(f"[warn] No source found for '{uri}'")
            self.respond("No source found - skipping song")
        else:
            await self.ass.queue_song(request)
