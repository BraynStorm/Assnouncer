from __future__ import annotations

from assnouncer.asspp import Identifier, Null
from assnouncer.commands.base import BaseCommand

from typing import List, Type


class Help(BaseCommand):
    ALIASES: List[str] = ["help", "halp"]

    async def on_command(self, name: Identifier = Null):
        """
        Print the documentation for a command or print all commands if absent.
        Call 112 in case this isn't what you're looking for.

        :param name: (Optional) Name of the command that you need help with.
        """
        if name != Null:
            command = BaseCommand.parse(name.value)
            command_type = BaseCommand.find_command(command)
            message = command_type.analyze().format()
        else:
            def format_aliases(command_type: Type[BaseCommand]) -> str:
                aliases = ", ".join(command_type.ALIASES)
                return f" - {aliases}"

            command_types = BaseCommand.get_instances()
            commands = "\n".join(map(format_aliases, command_types))
            message = (
                f"Assnouncer has the following commands:\n"
                f"{commands}"
            )

        self.respond(f"```{message}```")
