from __future__ import annotations

import asyncio
import time

from assnouncer import util
from assnouncer.commands.audio.player import AudioPlayer
from assnouncer.util import SongRequest
from assnouncer.commands import BaseCommand

from dataclasses import dataclass, field
from typing import List
from threading import RLock, Event, Thread
from pathlib import Path
from discord import (
    Client, Game, TextChannel, Message,
    Guild, VoiceClient, Member, VoiceState
)


@dataclass
class Assnouncer(Client):
    event: Event = field(default_factory=Event)
    lock: RLock = field(default_factory=RLock)
    song_queue: List[SongRequest] = field(default_factory=list)
    theme_queue: List[SongRequest] = field(default_factory=list)
    server: Guild = None
    general: TextChannel = None
    voice: VoiceClient = None

    def __post_init__(self):
        super().__init__()

    def skip(self):
        self.event.set()

    def stop(self):
        with self.lock:
            self.song_queue = []
            self.skip()

    def set_activity(self, activity: str):
        return self.change_presence(activity=Game(name=activity))

    def message(self, message: str, channel: TextChannel = None):
        if channel is None:
            channel = self.general

        return asyncio.run_coroutine_threadsafe(channel.send(message), self.loop)

    def song_loop(self):
        player = AudioPlayer(self.voice)
        while True:
            request: SongRequest
            with self.lock:
                if not self.song_queue and not self.theme_queue:
                    time.sleep(0.1)
                    continue

                if self.theme_queue:
                    request = self.theme_queue.pop(0)
                elif self.song_queue:
                    request = self.song_queue.pop(0)

            span = ""
            if request.start is not None or request.stop is not None:
                start = ""
                stop = ""

                if request.start is not None:
                    start = request.start.format()

                if request.stop is not None:
                    stop = request.stop.format()

                span = f"[{start}-{stop}]"

            self.message(f"Playing '{request.uri}' {span}")

            def callback() -> bool:
                with self.lock:
                    if self.event.is_set():
                        self.event.clear()

                        player.source = None

                        return True

                    if not self.theme_queue:
                        return False

                    request = self.theme_queue.pop(0)

                    old_source = player.source
                    player.source = request.source

                    player.run(callback=callback)

                    player.source = old_source

                    return True

            player.source = request.source

            self.event.clear()

            player.set_speaking(True)
            player.run(callback=callback)
            player.set_speaking(False)

    async def on_ready(self):
        print("[info] Getting ready")
        await self.set_activity("Getting ready")

        self.server = self.get_guild(642747343208185857)
        self.general = self.server.text_channels[0]
        self.voice = await self.server.voice_channels[0].connect(timeout=2000, reconnect=True)

        await self.set_activity("Ready")

        print("[info] Ready")

        Thread(target=self.song_loop, daemon=True).start()

    def queue_song(self, request: SongRequest):
        with self.lock:
            self.song_queue.append(request)

    async def play_theme(self, user: Member):
        theme_path = util.get_theme_path(user)
        source = await util.load_source(theme_path)

        if source is None:
            print(f"[warn] No theme for {user}")
            return

        with self.lock:
            request = SongRequest(
                source=source,
                query=f"{user}'s theme",
                uri=f"{user}'s theme"
            )

            self.theme_queue.append(request)

    async def on_voice_state_update(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState
    ):
        if member == self.user:
            return

        prev_channel = before.channel
        next_channel = after.channel
        if prev_channel is None and next_channel is not None:
            print(f"[chat] <{next_channel.name}>: {member} has joined")
            await self.play_theme(member)

    async def on_message(self, message: Message):
        if self.voice is None:
            return

        if message.author == self.user:
            return

        if "\n" in message.content:
            return

        print(f"[info] Parsing: {repr(message.content)}")
        try:
            command = BaseCommand.parse(message.content)
            print(f"[info] Trying to run '{command}'")
            await BaseCommand.run(self, message, command)
        except SyntaxError as e:
            print(f"[warn] {e}")
        except TypeError as e:
            print(f"[warn] {e}")


if __name__ == "__main__":
    ass = Assnouncer()
    ass.run(Path("token").read_text())
