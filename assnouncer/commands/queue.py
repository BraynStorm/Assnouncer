from __future__ import annotations

from assnouncer.commands.base import BaseCommand

from typing import List

from assnouncer.util import SongRequest


class Queue(BaseCommand):
    ALIASES: List[str] = ["queue", "q", "яуеуе"]

    async def on_command(self):
        """
        Print all songs in the queue.
        """
        def stringify(idx: int, song: SongRequest) -> str:
            if song.uri == song.query:
                return f"{idx}: {song.uri}"
            return f"{idx}: {song.uri} ({song.query})"

        queue_content = "\n".join(map(stringify, enumerate(self.ass.song_queue)))
        if not queue_content:
            queue_content = "Queue is empty."
        self.respond(f"```{queue_content}```")
