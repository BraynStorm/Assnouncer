from __future__ import annotations

import logging

from assnouncer import util
from assnouncer.asspp import String, Timestamp
from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, ClassVar

logger = logging.getLogger(__name__)


@dataclass
class Play(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["play", "Play", "плаъ", "πλαυ", "playing"]

    async def on_command(self, payload: String, start: Timestamp = None, stop: Timestamp = None):
        """
        Add a song to Assnouncer's queue.

        :param payload: Url or Youtube query for the song.
        :param start: (Optional) Start timestamp within the song.
        :param stop: (Optional) End timestamp within the song.
        """
        uri = await util.resolve_uri(payload.value)
        if uri is None:
            logger.warn(f"No source found for '{payload.value}'")
            await self.respond("No source found - skipping song")
        else:
            request = util.download(payload.value, uri, start=start, stop=stop, channel=self.channel)
            await self.ass.queue_song(request)
