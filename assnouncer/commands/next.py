from __future__ import annotations

from assnouncer.commands.base import BaseCommand

from typing import List


class Next(BaseCommand):
    ALIASES: List[str] = ["next", "skip", "маняк"]

    async def on_command(self):
        """
        Skip the current song.
        """
        self.ass.skip()