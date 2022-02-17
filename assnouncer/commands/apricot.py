from __future__ import annotations

import random

from assnouncer.commands.base import BaseCommand

from typing import List


class Apricot(BaseCommand):
    ALIASES: List[str] = ["кайсий", "кайсии", "apricot"]

    async def on_command(self):
        """
        Call upon the god of apricots to bring forth an apricot meme.
        """
        memes = [
            "https://memegenerator.net/img/instances/78370751.jpg",
            "https://i.imgflip.com/1zcw47.jpg",
            "https://www.memecreator.org/static/images/memes/4835791.jpg"
        ]
        self.respond(random.choice(memes))