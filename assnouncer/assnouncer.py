from __future__ import annotations

import time
import asyncio
import logging

from assnouncer import debug
from assnouncer import util
from assnouncer import config
from assnouncer import stats
from assnouncer.asspp import Timestamp
from assnouncer.util import SongRequest
from assnouncer.queue import Queue
from assnouncer.commands import BaseCommand
from assnouncer.audio import music
from assnouncer.audio.music import MusicState

from datetime import datetime
from dataclasses import dataclass, field
from typing import Awaitable, List, TypeVar, TYPE_CHECKING
from concurrent.futures import Future
from threading import Event, Thread
from asyncio import Lock
from discord import (
    Client,
    Game,
    TextChannel,
    Message,
    Guild,
    VoiceClient,
    Member,
    VoiceState,
    Intents,
    VoiceChannel,
    SpeakingState,
)

if TYPE_CHECKING:
    from discord.abc import MessageableChannel

T = TypeVar("T")


logger = logging.getLogger(__name__)


@dataclass
class Assnouncer(Client):
    skip_event: Event = field(default_factory=Event)
    song_queue: Queue[Future[SongRequest]] = field(default_factory=Queue)
    theme_queue: Queue[SongRequest] = field(default_factory=Queue)
    lock: Lock = field(default_factory=Lock)
    thread: Thread = None
    server: Guild = None
    general: TextChannel = None
    voice: VoiceClient = None

    def __post_init__(self):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

    def skip(self):
        self.skip_event.set()

    def stop(self):
        self.song_queue.clear()
        self.skip()

    async def set_activity(self, activity: str):
        return await self.change_presence(activity=Game(name=activity))

    async def set_speaking(self, speaking: SpeakingState):
        return await self.voice.ws.speak(speaking)

    async def message(self, message: str, channel: MessageableChannel = None):
        if channel is None:
            channel = self.general

        await channel.send(message)

    def run_coroutine(self, coro: Awaitable[T]) -> Future[T]:
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    @debug.profiled
    def reconnect_callback(self) -> VoiceClient:
        return self.run_coroutine(self.ensure_connected()).result()

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
            self.run_coroutine(self.set_speaking(SpeakingState.soundshare))
            music.play(
                request.source,
                reconnect_callback=self.reconnect_callback,
                state_callback=self.skip_callback,
            )

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

            uri = request.uri.replace("https://www.", "https://")

            stats.on_play_song(
                stats.Play(
                    url=uri,
                    request_text=request.query,
                    played_on=datetime.now(),
                    queued_on=request.queued_on,
                    queued_by=request.queued_by,
                    start=(request.start or Timestamp(-1, -1, -1)).value,
                    stop=(request.stop or Timestamp(-1, -1, -1)).value,
                )
            )
            self.run_coroutine(coro)

        self.skip_event.clear()

        self.run_coroutine(self.set_speaking(SpeakingState.soundshare))
        music.play(
            request.source,
            reconnect_callback=self.reconnect_callback,
            state_callback=self.theme_callback,
        )
        self.run_coroutine(self.set_speaking(SpeakingState.none))

    def song_loop(self):
        while True:
            request = self.theme_queue.pop() or self.song_queue.pop()
            if request is None:
                time.sleep(0.1)
                continue

            if isinstance(request, Future):
                request = request.result()

            if request is None:
                message = "Маняк на бота му стана лошо, няма такава песен"
                self.run_coroutine(self.message(message))
                continue

            self.handle_song(request)
            debug.print_report()

    @debug.profiled
    async def ensure_connected(self):
        async with self.lock:
            if self.voice is not None and self.voice.is_connected():
                return self.voice

            if self.voice is not None:
                logger.info("Trying to reconnect to voice")
                if await self.voice.potential_reconnect():
                    self.voice.resume()
                    return self.voice

            logger.info(f"Connecting to {config.GUILD_ID}")
            self.server: Guild = self.get_guild(config.GUILD_ID)
            self.general: TextChannel = self.server.text_channels[0]
            vc: VoiceChannel = self.server.voice_channels[0]

            while True:
                try:
                    self.voice = await vc.connect(timeout=10.0)
                    return self.voice
                except TimeoutError:
                    logger.warn(f"Failed to connect to {config.GUILD_ID}")

    async def on_ready(self):
        logger.info("Getting ready")
        await self.set_activity("Getting ready")
        await self.ensure_connected()
        await self.set_activity("Ready")
        logger.info("Ready")

        theme_path = util.get_theme_path("Assnouncer")
        theme_source = await util.load_source(theme_path)
        theme_request = SongRequest(
            source=theme_source,
            query="Assnouncer's theme",
            uri="Assnouncer's theme",
            channel=self.general,
            sneaky=True,
        )
        self.theme_queue.put(theme_request)

        if self.thread is None or not self.thread.is_alive():
            self.thread = Thread(target=self.song_loop, daemon=True)
            self.thread.start()

    async def queue_song(self, request: Awaitable[SongRequest]):
        await self.ensure_connected()

        self.song_queue.put(self.run_coroutine(request))

    async def play_theme(self, user: Member):
        await self.ensure_connected()

        theme_path = util.get_theme_path(user)

        source = await util.load_source(theme_path)
        if source is None:
            logger.warn(f"No theme for {user}")
            return

        request = SongRequest(
            source=source,
            query=f"{user}'s theme",
            uri=f"{user}'s theme",
            channel=self.general,
        )

        self.theme_queue.put(request)

    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        if member == self.user or member.guild != self.server:
            return

        prev_channel = before.channel
        next_channel = after.channel
        if prev_channel is None and next_channel is not None:
            print(f"[chat] <{next_channel.name}>: {member} has joined")
            await self.play_theme(member)

    async def on_message(self, message: Message):
        if message.guild != self.server:
            return

        if message.author == self.user:
            return

        voice_state = message.author.voice
        if (
            voice_state is None
            or self.voice.channel != voice_state.channel  # Not in the same voice
            or voice_state.deaf  # Can't hear (by server)
            or voice_state.self_deaf  # Can't hear (by themselves)
        ):
            # NOTE(bozho2):
            #   Reject commands by people not in the voice channel of the bot
            logger.info(
                f"Ignoring command from user {message.author.name}"
                " because they are not in the voice channel."
            )
            return

        # TODO: Move this to asspp.parse or BaseCommand

        content: str = message.content
        lines: List[str] = [content]
        if content.startswith("```ass\n") and content.endswith("```"):
            content = content[7:-3]

            lines = [line for line in content.splitlines() if line.strip()]
        elif "\n" in content:
            return

        logger.info(f"Parsing: {message.content!r}")
        await self.ensure_connected()

        for idx, line in enumerate(lines):
            try:
                command = BaseCommand.parse(line)
                logger.info(f"Trying to run '{command}'")
                await BaseCommand.run(self, message, command)
            except (SyntaxError, TypeError) as e:
                logger.warn(f"Command #{idx}: {e}")
