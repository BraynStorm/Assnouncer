from __future__ import annotations

from assnouncer.asspp import Identifier, String
from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, Union, ClassVar


@dataclass
class Dumb(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["dumb", "мамкамуипрасе", "dumbdumb"]

    async def on_command(self, who: Union[Identifier, String], howdumb: Union[Identifier, String] = None):
        """
        Fiercely insult another person and/or inanimate object.

        :param who: The entity that should be insulted.
        :param howdumb: (Optional) How dumb said entity is.
        """
        if howdumb is not None:
            msg = f"{who} is {howdumb} dumb"
        else:
            msg = f"{who} is dumb"

        self.respond(msg)
