from __future__ import annotations

from assnouncer.commands.base import BaseCommand

from typing import List


class Stop(BaseCommand):
    ALIASES: List[str] = ["stop", "dilyankata", ]

    async def on_command(self):
        """
        Tell Assnouncer to shut up.
        """
        self.ass.stop()
