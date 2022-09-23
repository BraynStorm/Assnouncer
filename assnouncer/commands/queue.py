from __future__ import annotations
from concurrent.futures import Future

from assnouncer.util import SongRequest
from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, Tuple, ClassVar


@dataclass
class Queue(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["queue", "Queue", "q", "яуеуе"]

    async def on_command(self):
        """
        Print all songs in the queue.
        """
        def stringify(fuck_you: Tuple[int, Future[SongRequest]]) -> str:
            idx, future = fuck_you
            song = future.result()
            if song.uri == song.query:
                return f"{idx}: {song.uri}"
            return f"{idx}: {song.uri} ({song.query})"

        queue_content = "\n".join(map(stringify, enumerate(self.ass.song_queue)))
        if not queue_content:
            queue_content = "Queue is empty."
        await self.respond(f"```{queue_content}```")
