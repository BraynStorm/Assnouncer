from __future__ import annotations

from assnouncer import util
from assnouncer.asspp import String, Timestamp
from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, ClassVar


@dataclass
class SetTheme(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["settheme", "set_theme"]

    async def on_command(self, payload: String, start: Timestamp = None, stop: Timestamp = None):
        """
        Set the login theme for the sending user.

        :param payload: Url or Youtube query for the song.
        :param start: (Optional) Start timestamp within the song.
        :param stop: (Optional) End timestamp within the song.
        """
        author = self.message.author
        uri = await util.resolve_uri(payload.value)
        if uri is not None:
            print(f"[info] Set theme for {author} to {uri}")
            await util.download(
                payload.value,
                uri,
                start=start,
                stop=stop,
                filename=util.get_theme_path(author),
                force=True
            )
        else:
            print(f"[warn] Could not set theme for {author}")
