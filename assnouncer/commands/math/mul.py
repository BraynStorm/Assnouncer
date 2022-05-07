from __future__ import annotations

from assnouncer.asspp import Number
from assnouncer.commands.base import BaseCommand

from typing import List, ClassVar


class Mul(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["mul"]

    async def on_command(self, a: Number, b: Number) -> Number:
        """
        Multiplies two numbers and return the result

        :param a: First number.
        :param b: Second number.
        """
        return a * b
