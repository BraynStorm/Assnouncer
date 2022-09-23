from __future__ import annotations

from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, ClassVar


@dataclass
class Next(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["next", "Next", "skip", "Skip", "маняк"]

    async def on_command(self):
        """
        Skip the current song.
        """
        self.ass.skip()
