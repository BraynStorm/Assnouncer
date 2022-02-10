from __future__ import annotations

from assnouncer.asspp import String
from assnouncer.commands.base import BaseCommand

from typing import List


class Print(BaseCommand):
    ALIASES: List[str] = ["print"]

    async def on_command(self, payload: String):
        """
        Execute a command in the payload and print the result.

        :param payload: The command line for another command.
        """
        command = BaseCommand.parse(payload.value)
        result = await BaseCommand.run(self.ass, self.message, command)
        self.respond(result.format())
