from __future__ import annotations

import util
import random
import commandline

from util import SongRequest
from commandline import Command, Timestamp, Identifier, String
from metaclass import Descriptor
from typing import TYPE_CHECKING, List, Union
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
        if song is not None:
            print(f"[info] Set theme for {author} to {song.uri}")
        else:
            print(f"[warn] Could not set theme for {author}")


class DumbCommand(BaseCommand):
    ALIASES: List[str] = ["dumb", "мамкамуипрасе", "dumbdumb"]

    @staticmethod
    async def on_command(
        ass: Assnouncer,
        _: Message,
        who: Union[Identifier, String],
        payload: str = None,
        howdumb: Union[Identifier, String] = None
    ):
        if howdumb is not None:
            msg = f"{who.value} is {howdumb.value} dumb"
        else:
            msg = f"{who.value} is dumb"

        await ass.message(msg)


class ApricotCommand(BaseCommand):
    ALIASES: List[str] = ["кайсий", "кайсии", "apricot"]

    @staticmethod
    async def on_command(
        ass: Assnouncer,
        _: Message,
        payload: str = None
    ):
        memes = [
            "https://memegenerator.net/img/instances/78370751.jpg",
            "https://i.imgflip.com/1zcw47.jpg",
            "https://www.memecreator.org/static/images/memes/4835791.jpg"
        ]
        await ass.message(random.choice(memes))
