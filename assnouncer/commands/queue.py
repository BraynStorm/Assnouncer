from __future__ import annotations

from assnouncer.commands.base import BaseCommand

from typing import List


class Queue(BaseCommand):
    ALIASES: List[str] = ["queue", "q", "яуеуе"]

    async def on_command(self):
        """
        Print all songs in the queue.
        """
        queue_content = "\n".join(
            f"{i}: {q}" for i, q in enumerate(self.ass.song_queue))
        if not queue_content:
            queue_content = "Queue is empty."
        self.respond(f"```{queue_content}```")
