from __future__ import annotations

import util

from util import SongRequest
from dataclasses import dataclass, field
from asyncio.tasks import sleep
from typing import List
from pathlib import Path
from commands import BaseCommand
from discord.player import AudioPlayer
from discord import (
    Client, Game, FFmpegOpusAudio, TextChannel,
    Message, Guild, VoiceClient, Member, VoiceState
)


@dataclass
class Assnouncer(Client):
    queue: List[SongRequest] = field(default_factory=list)
    server: Guild = None
    general: TextChannel = None
    voice: VoiceClient = None

    def __post_init__(self):
        super().__init__()

    def is_playing(self) -> bool:
        return self.voice.is_playing()

    def skip(self):
        self.voice.stop()

    def stop(self):
        self.queue = []
        self.skip()

    async def play_now(self, source: FFmpegOpusAudio):
        if self.voice.is_playing():
            old_source: AudioPlayer = self.voice._player
            old_source.pause()

            self.voice._player = None
            self.voice.play(source)
            while self.voice.is_playing():
                await sleep(0.3)
            self.voice.stop()

            self.voice._player = old_source
            self.voice.resume()
        else:
            self.voice.play(source)

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

        while True:
            while self.is_playing():
                if len(self.queue) > 1:
                    request = self.queue[1]
                    await util.download(request)
                await sleep(0.1)

            while not self.queue:
                await sleep(0.3)

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

            await self.message(f"Playing '{request.query}' {span}")
            song = await util.download(request)

            if song.source is not None:
                self.voice.play(song.source, after=pop)
            else:
                pop()
                print(f"[warn] No source found for '{song.uri}'")
                await self.message(f"No source found - skipping song")

    async def on_ready(self):
        print("[info] Getting ready")
        await self.set_activity("Getting ready")

        self.server = self.get_guild(642747343208185857)
        self.general = self.server.text_channels[0]
        self.voice = await self.server.voice_channels[0].connect(timeout=2000, reconnect=True)

        await self.set_activity("Ready")
        print("[info] Ready")

        return await self.song_loop()

    def queue_song(self, request: SongRequest):
        request.query = util.resolve_uri(request.query)
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

        for command_type in BaseCommand.get_instances():
            command = command_type.parse(message)
            if command is not None:
                print(f"[info] Received {command_type.__name__}")
                args = command.args or []
                kwargs = command.kwargs or {}
                await command_type.on_command(
                    self,
                    message,
                    *args,
                    payload=command.payload,
                    **kwargs
                )
                break


if __name__ == "__main__":
    ass = Assnouncer()
    ass.run(Path("token").read_text())
