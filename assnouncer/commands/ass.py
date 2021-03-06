from __future__ import annotations

from assnouncer.asspp import String
from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, ClassVar


@dataclass
class Ass(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["ass"]

    async def on_command(self, payload: String):
        """
        ASS - Activate Strict Syntax or something, idk.

        Execute a command in the payload and either print the result or the error if it fails.

        :param payload: The command line for another command.
        """
        try:
            command = BaseCommand.parse(payload.value)
            result = await BaseCommand.run(self.ass, self.message, command)

            if result is not None:
                await self.respond(f"Command result: {result}")
        except (SyntaxError, TypeError) as e:
            message = (
                f"Could not run command:\n"
                f"    {e.__class__.__name__}: {e}"
            )
            await self.respond(f"```{message}```")
