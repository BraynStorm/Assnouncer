from __future__ import annotations

import asyncio
import time

from assnouncer import util
from assnouncer.audio import music
from assnouncer.asspp import Null
from assnouncer.util import SongRequest
from assnouncer.audio.music import MusicState
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
    skip_event: Event = field(default_factory=Event)
    lock: RLock = field(default_factory=RLock)
    song_queue: List[SongRequest] = field(default_factory=list)
    theme_queue: List[SongRequest] = field(default_factory=list)
    server: Guild = None
    general: TextChannel = None
    voice: VoiceClient = None

    def __post_init__(self):
        super().__init__()

    def skip(self):
        self.skip_event.set()

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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def wait(coro):
            loop.run_until_complete(coro)

        while True:
            with self.lock:
                if not self.song_queue and not self.theme_queue:
                    time.sleep(0.1)
                    continue

                voice = self.voice

                if not voice.is_connected():
                    time.sleep(0.1)
                    continue

                if self.theme_queue:
                    request = self.theme_queue.pop(0)
                elif self.song_queue:
                    request = self.song_queue.pop(0)

            span = ""
            if request.start != Null or request.stop != Null:
                start = ""
                stop = ""

                if request.start != Null:
                    start = str(request.start)

                if request.stop != Null:
                    stop = str(request.stop)

                span = f"[{start}-{stop}]"

            self.message(f"Now playing \\` {request.uri} \\` {span}")

            def callback() -> bool:
                with self.lock:
                    if self.skip_event.is_set():
                        self.skip_event.clear()

                        return MusicState.STOPPED

                    if not self.theme_queue:
                        return MusicState.CONTINUED

                    request = self.theme_queue.pop(0)

                    music.play(voice, request.source, callback=callback)

                    return MusicState.INTERRUPTED

            self.skip_event.clear()

            wait(voice.ws.speak(True))
            music.play(voice, request.source, callback=callback)
            wait(voice.ws.speak(False))

            # Make sure request gets garbage collected as soon as possible
            del request

    async def ensure_connected(self):
        with self.lock:
            if self.voice is not None and self.voice.is_connected():
                return

            if self.voice is None:
                vc = self.server.voice_channels[0]
                self.voice = await vc.connect(timeout=2000, reconnect=True)
            else:
                await self.voice.connect(timeout=2000, reconnect=True)

    async def on_ready(self):
        print("[info] Getting ready")
        await self.set_activity("Getting ready")

        self.server = self.get_guild(642747343208185857)
        self.general = self.server.text_channels[0]

        await self.ensure_connected()

        await self.set_activity("Ready")

        print("[info] Ready")

        Thread(target=self.song_loop, daemon=True).start()

    async def queue_song(self, request: SongRequest):
        with self.lock:
            await self.ensure_connected()

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

            await self.ensure_connected()

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

        # TODO: Move this to asspp.parse or BaseCommand

        content: str = message.content
        lines: List[str] = [content]
        if content.startswith("```") and content.endswith("```"):
            content = content[3:-3]

            lines = [line for line in content.splitlines() if line.strip()]
            for idx, line in enumerate(lines):
                if not BaseCommand.can_run(line):
                    print(f"[warn] Cannot run command #{idx}: {line}")
                    return

        elif "\n" in content:
            return

        print(f"[info] Parsing: {message.content!r}")

        for idx, line in enumerate(lines):
            try:
                command = BaseCommand.parse(line)
                print(f"[info] Trying to run '{command}'")
                await BaseCommand.run(self, message, command)
            except (SyntaxError, TypeError) as e:
                print(f"[warn] Command #{idx}: {e}")

