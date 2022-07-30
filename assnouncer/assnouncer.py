from __future__ import annotations

import time
import asyncio

from assnouncer import debug
from assnouncer import util
from assnouncer import config
from assnouncer.util import SongRequest
from assnouncer.queue import Queue
from assnouncer.commands import BaseCommand
from assnouncer.audio import music
from assnouncer.audio.music import MusicState

from dataclasses import dataclass, field
from typing import Awaitable, List, TypeVar
from concurrent.futures import Future
from threading import Event, Thread
from discord import (
    Client, Game, TextChannel, Message,
    Guild, VoiceClient, Member, VoiceState,
    Intents, VoiceChannel
)

T = TypeVar("T")


@dataclass
class Assnouncer(Client):
    skip_event: Event = field(default_factory=Event)
    song_queue: Queue[Future[SongRequest]] = field(default_factory=Queue)
    theme_queue: Queue[SongRequest] = field(default_factory=Queue)
    thread: Thread = None
    server: Guild = None
    general: TextChannel = None
    voice: VoiceClient = None

    def __post_init__(self):
        super().__init__(intents=Intents.default())

    def skip(self):
        self.skip_event.set()

    def stop(self):
        self.song_queue.clear()
        self.skip()

    async def set_activity(self, activity: str):
        return await self.change_presence(activity=Game(name=activity))

    async def set_speaking(self, speaking: bool):
        return await self.voice.ws.speak(speaking)

    async def message(self, message: str, channel: TextChannel = None):
        if channel is None:
            channel = self.general

        await channel.send(message)

    def run_coroutine(self, coro: Awaitable[T]) -> Future[T]:
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    @debug.profiled
    def skip_callback(self) -> MusicState:
        if self.skip_event.is_set():
            self.skip_event.clear()

            return MusicState.STOPPED
        return MusicState.CONTINUED

    @debug.profiled
    def theme_callback(self) -> MusicState:
        state = self.skip_callback()
        if state is MusicState.STOPPED:
            return MusicState.STOPPED

        while not self.theme_queue.empty():
            state = MusicState.INTERRUPTED

            request = self.theme_queue.pop()
            music.play(self.voice, request.source, callback=self.skip_callback)

        return state

    @debug.profiled
    def handle_song(self, request: SongRequest):
        if not request.sneaky:
            parts = ["Playing", request.uri]
            if (request.start, request.stop) != (None, None):
                start = "<"
                stop = ">"

                if request.start is not None:
                    start = str(request.start)

                if request.stop is not None:
                    stop = str(request.stop)

                parts.append(f"[{start}-{stop}]")

            if request.uri != request.query:
                parts.append(f"({request.query!r})")

            coro = self.message(" ".join(parts), channel=request.channel)
            self.run_coroutine(coro)

        self.skip_event.clear()

        self.run_coroutine(self.ensure_connected())

        self.run_coroutine(self.set_speaking(True))
        music.play(self.voice, request.source, callback=self.theme_callback)
        self.run_coroutine(self.set_speaking(False))

    def song_loop(self):
        while True:
            if self.song_queue.empty() and self.theme_queue.empty():
                time.sleep(0.1)
                continue

            if not self.voice.is_connected():
                time.sleep(0.1)
                continue

            request = self.theme_queue.pop() or self.song_queue.pop().result()
            self.handle_song(request)
            debug.print_report()

    @debug.profiled
    async def ensure_connected(self):
        if self.voice is not None and self.voice.is_connected():
            return

        if self.voice is not None:
            print("[info] Trying to reconnect to voice")
            await self.voice.disconnect(force=True)

        print(f"[info] Connecting to {config.GUILD_ID}")
        self.server: Guild = self.get_guild(config.GUILD_ID)
        self.general: TextChannel = self.server.text_channels[0]

        vc: VoiceChannel = self.server.voice_channels[0]
        self.voice = await vc.connect()

    async def on_ready(self):
        print("[info] Getting ready")
        await self.set_activity("Getting ready")

        await self.ensure_connected()

        await self.set_activity("Ready")
        print("[info] Ready")

        if self.thread is None or not self.thread.is_alive():
            self.thread = Thread(target=self.song_loop)
            self.thread.start()

    async def queue_song(self, request: Awaitable[SongRequest]):
        await self.ensure_connected()

        self.song_queue.put(self.run_coroutine(request))

    async def play_theme(self, user: Member):
        theme_path = util.get_theme_path(user)
        source = await util.load_source(theme_path)

        if source is None:
            print(f"[warn] No theme for {user}")
            return

        await self.ensure_connected()

        request = SongRequest(
            source=source,
            query=f"{user}'s theme",
            uri=f"{user}'s theme",
            channel=self.general
        )

        self.theme_queue.put(request)

    async def on_voice_state_update(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState
    ):
        if member == self.user or member.guild != self.server:
            return

        prev_channel = before.channel
        next_channel = after.channel
        if prev_channel is None and next_channel is not None:
            print(f"[chat] <{next_channel.name}>: {member} has joined")
            await self.play_theme(member)

    async def on_message(self, message: Message):
        if self.voice is None or message.guild != self.server:
            return

        if message.author == self.user:
            return

        # TODO: Move this to asspp.parse or BaseCommand

        content: str = message.content
        lines: List[str] = [content]
        if content.startswith("```ass\n") and content.endswith("```"):
            content = content[7:-3]

            lines = [line for line in content.splitlines() if line.strip()]
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
