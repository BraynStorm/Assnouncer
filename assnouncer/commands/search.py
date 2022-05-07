from __future__ import annotations

from assnouncer import util
from assnouncer.asspp import String
from assnouncer.commands.base import BaseCommand

from typing import List, ClassVar


class Search(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["search", "find"]

    async def on_command(self, payload: String) -> String:
        """
        Returns the Youtube url for a song query.

        :param payload: Url or Youtube query for the song.
        """
        return String.parse(payload.start, payload.stop, util.resolve_uri(payload.value), evaluate=False)
