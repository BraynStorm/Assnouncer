from __future__ import annotations
from sqlite3 import Timestamp

import util
import commandline

from util import SongRequest
from commandline import Command, Timestamp
from metaclass import Descriptor
from typing import TYPE_CHECKING, List
from discord import Message

if TYPE_CHECKING:
    from assnouncer import Assnouncer


class BaseCommand(metaclass=Descriptor):
    TYPE: Command = None
    ALIASES: List[str] = None

    @classmethod
    def validate(cls):
        if cls == BaseCommand:
            return

        msg = "ALIASES must be a non-empty list of str"
        assert cls.ALIASES, msg
        assert isinstance(cls.ALIASES, list), msg
        assert all(isinstance(k, str) for k in cls.ALIASES), msg

    @classmethod
    def parse(cls, message: Message) -> Command:
        content: str = message.content
        command = commandline.parse(content)

        if command.name.value in cls.ALIASES:
            return command

    @staticmethod
    async def on_command(
        ass: Assnouncer,
        message: Message,
        *args,
        payload: str = None,
        **kwargs
    ):
        pass


class PlayCommand(BaseCommand):
    ALIASES: List[str] = ["play"]

    @staticmethod
    async def on_command(
        ass: Assnouncer,
        _: Message,
        payload: str,
        start: Timestamp = None,
        stop: Timestamp = None
    ):
        ass.queue_song(SongRequest(query=payload, start=start, stop=stop))


class QueueCommand  (BaseCommand):
    ALIASES: List[str] = ["queue"]

    @staticmethod
    async def on_command(ass: Assnouncer, _: Message, payload: str = None):
        queue_content = "\n".join(f"{i}: {q}" for i, q in enumerate(ass.queue))
        if not queue_content:
            queue_content = "Queue is empty."
        await ass.message(f"```{queue_content}```")


class StopCommand(BaseCommand):
    ALIASES: List[str] = [
        "stop",
        "dilyankata",
    ]

    @staticmethod
    async def on_command(ass: Assnouncer, _: Message, payload: str = None):
        ass.stop()


class NextCommand(BaseCommand):
    ALIASES: List[str] = ["next", "skip", "маняк"]

    @staticmethod
    async def on_command(ass: Assnouncer, _: Message, payload: str = None):
        ass.skip()


class SetThemeCommand(BaseCommand):
    ALIASES: List[str] = ["settheme", "set_theme"]

    @staticmethod
    async def on_command(
        _: Assnouncer,
        message: Message,
        payload: str,
        start: Timestamp = None,
        stop: Timestamp = None
    ):
        author = message.author
        song = await util.download(
            SongRequest(query=payload, start=start, stop=stop),
            filename=util.get_theme_path(author),
            force=True
        )
        print(f"[info] Set theme for {author} to {song.uri}")
