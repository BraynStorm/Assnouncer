from __future__ import annotations

from assnouncer.commands.base import BaseCommand

from typing import List, ClassVar


class Stop(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["stop", "dilyankata", ]

    async def on_command(self):
        """
        Tell Assnouncer to shut up.
        """
        self.ass.stop()
