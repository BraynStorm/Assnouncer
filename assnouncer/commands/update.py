from __future__ import annotations

import asyncio

from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, ClassVar


@dataclass
class Update(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["update"]

    async def on_command(self):
        """
        Update yt-dlp which has been a pain in the ass(nouncer) for some time.
        """
        await asyncio.create_subprocess_shell("pip install -U yt-dlp")
