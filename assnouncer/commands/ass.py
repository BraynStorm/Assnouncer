from __future__ import annotations

from assnouncer.asspp import Null, String
from assnouncer.commands.base import BaseCommand

from typing import List


class Ass(BaseCommand):
    ALIASES: List[str] = ["ass"]

    async def on_command(self, payload: String):
        """
        ASS - Activate Strict Syntax or something, idk.

        Execute a command in the payload and either print the result or the error if it fails.

        :param payload: The command line for another command.
        """
        try:
            command = BaseCommand.parse(payload.value)
            result = await BaseCommand.run(self.ass, self.message, command)

            if result != Null:
                self.respond(f"Command result: {result}")
        except (SyntaxError, TypeError) as e:
            message = (
                f"Could not run command:\n"
                f"    {e.__class__.__name__}: {e}"
            )
            self.respond(f"```{message}```")
