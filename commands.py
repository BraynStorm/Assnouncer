from __future__ import annotations

import util

from metaclass import Descriptor
from dataclasses import dataclass
from typing import TYPE_CHECKING, List
from enum import unique, IntEnum
from discord import Message

if TYPE_CHECKING:
    from assnouncer import Assnouncer


@unique
class CommandType(IntEnum):
    BEGIN = 0
    EXACT = 1
    END = 2


@dataclass
class CommandData:
    message: Message
    parse_method: CommandType
    keyword: str
    argument: str = None
    payload: str = None


class BaseCommand(metaclass=Descriptor):
    TYPE: CommandType = None
    KEYWORDS: List[str] = None

    @classmethod
    def validate(cls):
        if cls == BaseCommand:
            return

        msg = "TYPE must be a CommandType"
        assert isinstance(cls.TYPE, CommandType), msg

        msg = "KEYWORDS must be a non-empty list of str"
        assert cls.KEYWORDS, msg
        assert isinstance(cls.KEYWORDS, list), msg
        assert all(isinstance(k, str) for k in cls.KEYWORDS), msg

    @classmethod
    def parse(cls, message: Message) -> CommandData:
        content: str = message.content
        for keyword in cls.KEYWORDS:
            def make_data(argument: str = None):
                return CommandData(
                    message=message,
                    parse_method=cls.TYPE,
                    keyword=keyword,
                    argument=argument
                )

            if cls.TYPE is CommandType.BEGIN:
                if content.startswith(keyword):
                    return make_data(argument=content[len(keyword):])
            elif cls.TYPE is CommandType.EXACT:
                if content == keyword:
                    return make_data()
            elif cls.TYPE is CommandType.END:
                if content.endswith(keyword):
                    return make_data(argument=content[:-len(keyword)])

    @staticmethod
    async def on_command(ass: Assnouncer, data: CommandData):
        pass


class PlayCommand(BaseCommand):
    TYPE: CommandType = CommandType.BEGIN
    KEYWORDS: List[str] = ["play "]

    @staticmethod
    async def on_command(ass: Assnouncer, data: CommandData):
        ass.queue_song(data.payload)


class QueueCommand  (BaseCommand):
    TYPE: CommandType = CommandType.EXACT
    KEYWORDS: List[str] = ["queue"]

    @staticmethod
    async def on_command(ass: Assnouncer, _: CommandData):
        queue_content = "\n".join(f"{i}: {q}" for i, q in enumerate(ass.queue))
        if not queue_content:
            queue_content = "Queue is empty."
        await ass.message(f"```{queue_content}```")


class StopCommand(BaseCommand):
    TYPE: CommandType = CommandType.EXACT
    KEYWORDS: List[str] = [
        "stop",
        "dilyankata",
        "не ме занимавай с твоите глупости"
    ]

    @staticmethod
    async def on_command(ass: Assnouncer, _: CommandData):
        ass.stop()


class NextCommand(BaseCommand):
    TYPE: CommandType = CommandType.EXACT
    KEYWORDS: List[str] = ["next", "skip", "маняк"]

    @staticmethod
    async def on_command(ass: Assnouncer, _: CommandData):
        ass.skip()


class SetThemeCommand(BaseCommand):
    TYPE: CommandType = CommandType.BEGIN
    KEYWORDS: List[str] = ["set my theme ", "set theme "]

    @staticmethod
    async def on_command(_: Assnouncer, data: CommandData):
        author = data.message.author
        song = await util.download(
            data.payload,
            filename=util.get_theme_path(author),
            force=True
        )
        print(f"[info] Set theme for {author} to {song.uri}")
