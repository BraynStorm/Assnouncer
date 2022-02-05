from __future__ import annotations

import util

from util import LoadedSong
from dataclasses import dataclass, field
from asyncio.tasks import sleep
from typing import List
from pathlib import Path
from discord.player import AudioPlayer
from discord import Client, Game, FFmpegOpusAudio, TextChannel, Message, Guild, VoiceClient, Member, VoiceState
from commands import BaseCommand


@dataclass
class Assnouncer(Client):
    queue: List[str] = field(default_factory=list)
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

    async def download_from_queue(self, idx: int) -> LoadedSong:
        if len(self.queue) > idx:
            uri = self.queue[idx]
            return await util.download(uri)

    async def song_loop(self):
        def pop(*_):
            if self.queue:
                self.queue.pop(0)

        while True:
            while self.is_playing():
                if len(self.queue) > 1:
                    await util.download(self.queue[1])
                await sleep(0.1)

            while not self.queue:
                await sleep(0.3)

            song = await util.download(self.queue[0])

            await self.message(f"Playing '{song.uri}'")

            if song.source is not None:
                self.voice.play(song.source, after=pop)
            else:
                print(f"[warn] No source found for '{song.uri}'")
                pop()
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

    def queue_song(self, query: str):
        self.queue.append(query)

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

        for command in BaseCommand.get_instances():
            command_args = command.parse(message)
            if command_args is not None:
                print(f"[info] Received {command.__name__}")
                await command.on_command(self, command_args)
                break


if __name__ == "__main__":
    ass = Assnouncer()
    ass.run(Path("token").read_text())
