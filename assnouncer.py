from __future__ import annotations

import util

from util import SongRequest
from dataclasses import dataclass, field
from asyncio.tasks import sleep
from typing import List
from threading import Event
from pathlib import Path
from commands import BaseCommand
from discord.player import AudioPlayer
from discord import (
    Client, Game, FFmpegOpusAudio, TextChannel,
    Message, Guild, VoiceClient, Member, VoiceState
)


@dataclass
class Assnouncer(Client):
    play_event: Event = field(default_factory=Event)
    queue: List[SongRequest] = field(default_factory=list)
    server: Guild = None
    general: TextChannel = None
    voice: VoiceClient = None

    def __post_init__(self):
        super().__init__()

    def is_playing(self) -> bool:
        return self.play_event.is_set()

    def skip(self):
        self.voice.stop()

        self.play_event.clear()

    def stop(self):
        self.queue = []
        self.skip()

    async def play_now(self, source: FFmpegOpusAudio):
        if self.is_playing():
            old_source: AudioPlayer = self.voice._player
            old_source.pause(update_speaking=False)

            event = Event()

            def unset(*_):
                event.set()

            self.voice._player = None
            self.voice.play(source, after=unset)

            event.wait()

            self.voice._player = old_source
            self.voice.resume()
        else:
            self.play_event.set()

            def unset(*_):
                self.play_event.set()

            self.voice.play(source, after=unset)

    def set_activity(self, activity: str):
        return self.change_presence(activity=Game(name=activity))

    def message(self, message: str, channel: TextChannel = None):
        if channel is None:
            channel = self.general

        return channel.send(message)

    async def song_loop(self):
        def pop(*_):
            if self.queue:
                self.queue.pop(0)

            self.skip()

        while True:
            if not self.queue:
                await sleep(0.1)
                continue
                
            if self.is_playing():
                await sleep(0.1)
                continue

            self.play_event.set()

            request = self.queue[0]

            span = ""
            if request.start is not None or request.stop is not None:
                start = ""
                stop = ""

                if request.start is not None:
                    start = request.start.text

                if request.stop is not None:
                    stop = request.stop.text
                span = f"[{start}-{stop}]"

            await self.message(f"Playing '{request.uri}' {span}")
            self.voice.play(request.source, after=pop)

    async def on_ready(self):
        print("[info] Getting ready")
        await self.set_activity("Getting ready")

        self.server = self.get_guild(642747343208185857)
        self.general = self.server.text_channels[0]
        self.voice = await self.server.voice_channels[0].connect(timeout=2000, reconnect=True)

        await self.set_activity("Ready")

        print("[info] Ready")

        # main_theme = await util.download(
        #     SongRequest(
        #         query="https://www.youtube.com/watch?v=atuFSv2bLa8",
        #         start=Timestamp.parse("00:19"),
        #         stop=Timestamp.parse("00:23")
        #     )
        # )
        # await self.play_now(main_theme.source)

        return await self.song_loop()

    def queue_song(self, request: SongRequest):
        self.queue.append(request)

    async def play_theme(self, user: Member):
        theme_path = util.get_theme_path(user)
        new_source = util.load_source(theme_path)

        if new_source is None:
            print(f"[warn] No theme for {user}")
        else:
            await self.play_now(await new_source)

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
            await BaseCommand.run(self, message, command)
        except SyntaxError as e:
            print(f"[warn] {e}")
        except TypeError as e:
            print(f"[warn] {e}")


if __name__ == "__main__":
    ass = Assnouncer()
    ass.run(Path("token").read_text())
