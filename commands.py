from __future__ import annotations

from metaclass import Descriptor
from dataclasses import dataclass
from typing import TYPE_CHECKING, List
from enum import unique, IntEnum

if TYPE_CHECKING:
    from assnouncer import Assnouncer


@unique
class CommandType(IntEnum):
    BEGIN = 0
    EXACT = 1
    END = 2


@dataclass
class CommandArgs:
    parse_method: CommandType
    keyword: str
    argument: str = None


class BaseCommand(metaclass=Descriptor):
    KEYWORDS: List[str] = None
    TYPE: CommandType = None

    @classmethod
    def parse(cls, content: str) -> CommandArgs:
        for keyword in cls.KEYWORDS:
            if cls.TYPE is CommandType.BEGIN:
                if content.startswith(keyword):
                    return CommandArgs(
                        parse_method=cls.TYPE,
                        keyword=keyword,
                        argument=content[len(keyword):]
                    )
            elif cls.TYPE is CommandType.EXACT:
                if content == keyword:
                    return CommandArgs(
                        parse_method=cls.TYPE,
                        keyword=keyword
                    )
            elif cls.TYPE is CommandType.END:
                if content.endswith(keyword):
                    return CommandArgs(
                        parse_method=cls.TYPE,
                        keyword=keyword,
                        argument=content[:-len(keyword)]
                    )

    @staticmethod
    async def on_command(ass: Assnouncer, message: CommandArgs):
        pass


class PlayCommand(BaseCommand):
    KEYWORDS: List[str] = ["play "]
    TYPE: CommandType = CommandType.BEGIN

    @staticmethod
    async def on_command(ass: Assnouncer, message: CommandArgs):
        ass.queue_song(message.argument)


class QueueCommand  (BaseCommand):
    KEYWORDS: List[str] = ["queue"]
    TYPE: CommandType = CommandType.EXACT

    @staticmethod
    async def on_command(ass: Assnouncer, _: CommandArgs):
        queue_content = "\n".join(f"{i}: {q}" for i, q in enumerate(ass.queue))
        if not queue_content:
            queue_content = "Queue is empty."
        await ass.message(f"```{queue_content}```")


class StopCommand(BaseCommand):
    KEYWORDS: List[str] = [
        "stop",
        "dilyankata",
        "не ме занимавай с твоите глупости"
    ]
    TYPE: CommandType = CommandType.EXACT

    @staticmethod
    async def on_command(ass: Assnouncer, _: CommandArgs):
        ass.stop()

        
class NextCommand(BaseCommand):
    KEYWORDS: List[str] = ["next", "skip", "маняк"]
    TYPE: CommandType = CommandType.EXACT

    @staticmethod
    async def on_command(ass: Assnouncer, _: CommandArgs):
        ass.skip()
