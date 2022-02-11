from __future__ import annotations

from assnouncer.asspp import Identifier, String, Null
from assnouncer.commands.base import BaseCommand

from typing import List, Union


class Dumb(BaseCommand):
    ALIASES: List[str] = ["dumb", "мамкамуипрасе", "dumbdumb"]

    async def on_command(
        self,
        who: Union[Identifier, String],
        howdumb: Union[Identifier, String] = Null
    ):
        """
        Fiercly insult another person and/or inanimate object.

        :param who: The entity that should be insulted.
        :param howdumb: (Optional) How dumb said entity is.
        """
        if howdumb != Null:
            msg = f"{who.value} is {howdumb.value} dumb"
        else:
            msg = f"{who.value} is dumb"

        self.respond(msg)
