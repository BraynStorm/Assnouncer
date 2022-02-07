from __future__ import annotations
from dataclasses import dataclass
import inspect

import util
import random
import commandline

from util import SongRequest
from commandline import Command, Timestamp, Number, Identifier, String, Value
from metaclass import Descriptor
from typing import TYPE_CHECKING, Any, List, Dict, Union, Type
from discord import Message, TextChannel

if TYPE_CHECKING:
    from assnouncer import Assnouncer


@dataclass
class Parameter:
    name: str
    hint: Any
    default: Any


@dataclass
class Help:
    aliases: List[str]
    docstring: str
    parameters: List[Parameter]

    def index(self, key: str) -> int:
        for idx, parameter in enumerate(self.parameters):
            if parameter.name == key:
                return idx

    def validate_type(self, value: Value, type: str) -> bool:
        if type.startswith("Union["):
            args = type[6:-1].split(", ")
            return any(self.validate_type(value, arg) for arg in args)

        return value.__class__.__name__ == type

    def validate(self, args: List[Value], kwargs: Dict[str, Value]):
        if len(args) > len(self.parameters):
            raise TypeError(
                f"Too many arguments given: "
                f"Expected {len(self.parameters)}, got {len(args)}"
            )

        for idx, value in enumerate(args):
            parameter = self.parameters[idx]
            name = parameter.name
            hint = parameter.hint
            if not self.validate_type(value, hint):
                raise TypeError(
                    f"Invalid type for parameter {name}: "
                    f"Expected {hint}, got {value.__class__.__name__}"
                )

        for key, value in kwargs.items():
            idx = self.index(key)
            if idx is None:
                raise TypeError(f"Unknown parameter '{key}'")

            if idx < len(args):
                raise TypeError(f"Parameter '{key}' specified twice")

            parameter = self.parameters[idx]
            name = parameter.name
            hint = parameter.hint
            if not self.validate_type(value, hint):
                raise TypeError(
                    f"Invalid type for parameter {name}: "
                    f"Expected {hint}, got {type(value)}"
                )

        for parameter in self.parameters[len(args):]:
            name = parameter.name
            default = parameter.default
            if name not in kwargs and default is ...:
                raise TypeError(f"Mandatory parameter {name} not specified")

    def format(self) -> str:
        def format_parameter(parameter: Parameter) -> str:
            if parameter.default is ...:
                return f"{parameter.name}: {parameter.hint}"

            return f"{parameter.name}: {parameter.hint} = {parameter.default}"

        aliases = ", ".join(self.aliases)
        signature = ", ".join(map(format_parameter, self.parameters))

        doc = (
            f"Aliases: {aliases}\n"
            f"Signature: [{signature}]\n"
            f"\n"
            f"{self.docstring}"
        )

        return inspect.cleandoc(doc)

    def __contains__(self, key: str) -> bool:
        return self.index(key) is not None


class BaseCommand(metaclass=Descriptor):
    TYPE: Command = None
    ALIASES: List[str] = None

    def __init__(self, ass: Assnouncer, message: Message) -> None:
        self.ass: Assnouncer = ass
        self.message: Message = message
        self.channel: TextChannel = message.channel

    @classmethod
    def validate(cls):
        if cls == BaseCommand:
            return

        msg = "ALIASES must be a non-empty list of str"
        assert cls.ALIASES, msg
        assert isinstance(cls.ALIASES, list), msg
        assert all(isinstance(k, str) for k in cls.ALIASES), msg

    @staticmethod
    def parse(content: str) -> Command:
        return commandline.parse(content)

    @classmethod
    def accept(cls, command: Command) -> bool:
        return command.name in cls.ALIASES

    @staticmethod
    def find_command(command: Command) -> Type[BaseCommand]:
        for command_type in BaseCommand.get_instances():
            if command_type.accept(command):
                return command_type

    @staticmethod
    async def run(ass: Assnouncer, message: Message, command: Command):
        command_type = BaseCommand.find_command(command)
        if command_type is None:
            return

        print(f"[info] Received {command_type.__name__}")

        args = command.args or []
        kwargs = command.kwargs or {}

        help = command_type.analyze()
        if "payload" in help and "payload" not in kwargs:
            payload = String.parse(command.payload, unescape=False)
            kwargs.update(payload=payload)

        help.validate(args, kwargs)

        instance = command_type(ass, message)
        return await instance.on_command(*args, **kwargs)

    @classmethod
    def analyze(cls) -> Help:
        aliases = cls.ALIASES
        docstring = inspect.getdoc(cls.on_command)
        parameters = []

        signature = inspect.signature(cls.on_command)
        for value in signature.parameters.values():
            name = value.name
            hint = value.annotation
            default = value.default

            if name == "self":
                continue

            if default is inspect._empty:
                default = ...

            parameter = Parameter(name=name, hint=hint, default=default)
            parameters.append(parameter)

        return Help(aliases=aliases, docstring=docstring, parameters=parameters)

    async def on_command(self, *args, **kwargs):
        pass


class AssCommand(BaseCommand):
    ALIASES: List[str] = ["ass"]

    async def on_command(self, payload: String):
        """
        ASS - Activate String Syntax or something, idk.

        Execute a command in the payload and print in case it fails.

        :param payload: The command line for another command.
        """
        try:
            command = BaseCommand.parse(payload.value)
            await BaseCommand.run(self.ass, self.message, command)
        except SyntaxError as e:
            message = (
                f"Could not parse command:\n"
                f"    {e}"
            )
            await self.ass.message(
                f"```{message}```",
                channel=self.channel
            )
        except TypeError as e:
            message = (
                f"Invalid command arguments:\n"
                f"    {e}"
            )
            await self.ass.message(
                f"```{message}```",
                channel=self.channel
            )


class HelpCommand(BaseCommand):
    ALIASES: List[str] = ["help", "halp"]

    async def on_command(self, name: Identifier = None):
        """
        Print the documentation for a command or print all commands if absent.
        Call 112 in case this isn't what you're looking for.

        :param name: (Optional) Name of the command that you need help with.
        """
        if name is not None:
            command = BaseCommand.parse(name.value)
            command_type = BaseCommand.find_command(command)
            message = command_type.analyze().format()
        else:
            def format_aliases(command_type: Type[BaseCommand]) -> str:
                aliases = ", ".join(command_type.ALIASES)
                return f" - {aliases}"

            command_types = BaseCommand.get_instances()
            commands = "\n".join(map(format_aliases, command_types))
            message = (
                f"Assnouncer has the following commands:\n"
                f"{commands}"
            )

        await self.ass.message(f"```{message}```", channel=self.channel)


class PlayCommand(BaseCommand):
    ALIASES: List[str] = ["play", "плаъ"]

    async def on_command(
        self,
        payload: String,
        start: Union[Timestamp, Number] = None,
        stop: Union[Timestamp, Number] = None
    ):
        """
        Add a song to Assnouncer's queue.

        :param payload: Url or Youtube query for the song.
        :param start: (Optional) Start timestamp within the song.
        :param stop: (Optional) End timestamp within the song.
        """
        request = await util.download(payload.value, start=start, stop=stop)
        if request is None:
            uri = util.resolve_uri(payload.value)
            print(f"[warn] No source found for '{uri}'")
            await self.message(f"No source found - skipping song")
        else:
            self.ass.queue_song(request)


class QueueCommand  (BaseCommand):
    ALIASES: List[str] = ["queue", "q"]

    async def on_command(self):
        """
        Print all songs in the queue.
        """
        queue_content = "\n".join(
            f"{i}: {q}" for i, q in enumerate(self.ass.queue))
        if not queue_content:
            queue_content = "Queue is empty."
        await self.ass.message(f"```{queue_content}```")


class StopCommand(BaseCommand):
    ALIASES: List[str] = ["stop", "dilyankata", ]

    async def on_command(self):
        """
        Tell Assnouncer to shut up.
        """
        self.ass.stop()


class NextCommand(BaseCommand):
    ALIASES: List[str] = ["next", "skip", "маняк"]

    async def on_command(self):
        """
        Skip the current song.
        """
        self.ass.skip()


class SetThemeCommand(BaseCommand):
    ALIASES: List[str] = ["settheme", "set_theme"]

    async def on_command(
        self,
        payload: String,
        start: Union[Timestamp, Number] = None,
        stop: Union[Timestamp, Number] = None
    ):
        """
        Set the login theme for the sending user.

        :param payload: Url or Youtube query for the song.
        :param start: (Optional) Start timestamp within the song.
        :param stop: (Optional) End timestamp within the song.
        """
        author = self.message.author
        request = SongRequest(query=payload.value, start=start, stop=stop)
        song = await util.download(
            request,
            filename=util.get_theme_path(author),
            force=True
        )
        if song is not None:
            print(f"[info] Set theme for {author} to {song.uri}")
        else:
            print(f"[warn] Could not set theme for {author}")


class DumbCommand(BaseCommand):
    ALIASES: List[str] = ["dumb", "мамкамуипрасе", "dumbdumb"]

    async def on_command(
        self,
        who: Union[Identifier, String],
        howdumb: Union[Identifier, String] = None
    ):
        """
        Fiercly insult another person and/or inanimate object.

        :param who: The entity that should be insulted.
        :param howdumb: (Optional) How dumb said entity is.
        """
        if howdumb is not None:
            msg = f"{who.value} is {howdumb.value} dumb"
        else:
            msg = f"{who.value} is dumb"

        await self.ass.message(msg)


class ApricotCommand(BaseCommand):
    ALIASES: List[str] = ["кайсий", "кайсии", "apricot"]

    async def on_command(self):
        """
        Call upon the god of apricots to bring forth an apricot meme.
        """
        memes = [
            "https://memegenerator.net/img/instances/78370751.jpg",
            "https://i.imgflip.com/1zcw47.jpg",
            "https://www.memecreator.org/static/images/memes/4835791.jpg"
        ]
        await self.ass.message(random.choice(memes))
