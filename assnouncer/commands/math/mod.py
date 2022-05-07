from __future__ import annotations

from assnouncer.asspp import Number
from assnouncer.commands.base import BaseCommand

from typing import List, ClassVar


class Mod(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["mod"]

    async def on_command(self, a: Number, b: Number) -> Number:
        """
        Calculates the modulo of two numbers and return the result

        :param a: First number.
        :param b: Second number.
        """
        return a % b
