from __future__ import annotations

from assnouncer.asspp import Command, String
from assnouncer.commands.base import BaseCommand

from typing import List


class Parse(BaseCommand):
    ALIASES: List[str] = ["parse"]

    async def on_command(self, payload: String) -> Command:
        """
        Parses a command given in the payload and returns the AST

        :param payload: The command line for another command.
        """
        return BaseCommand.parse(payload.value)
