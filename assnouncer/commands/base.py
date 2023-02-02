from __future__ import annotations

import inspect
import logging

from assnouncer import asspp
from assnouncer import util
from assnouncer.asspp import Command, Null, Timestamp, String, Identifier, Number, Value, Expression
from assnouncer.metaclass import Descriptor

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, List, Tuple, Type
from discord import Message

if TYPE_CHECKING:
    from assnouncer.assnouncer import Assnouncer
    
    from discord.abc import MessageableChannel

logger = logging.getLogger(__name__)


@dataclass
class Parameter:
    name: str
    type: Any
    default: Any


@dataclass
class Help:
    aliases: List[str]
    docstring: str
    parameters: List[Parameter]
    return_type: Any

    def index(self, key: str) -> int:
        for idx, parameter in enumerate(self.parameters):
            if parameter.name == key:
                return idx
        return None

    def validate_type(self, value: Value, type: str, default: Expression = None) -> bool:
        if value is None:
            return False

        if type.startswith("Union["):
            args = type[6:-1].split(", ")
            return any(self.validate_type(value, arg, default=default) for arg in args)

        if value is default:
            return True

        supported_types: List[Type[Expression]] = [
            Expression,
            Value,
            Number,
            Identifier,
            String,
            Timestamp
        ]
        type_map = {t.__name__: t for t in supported_types}
        if type not in type_map:
            raise TypeError(f"Unsupported type annotation: {type}")

        return isinstance(value, type_map[type])

    def validate(self, args: List[Value], kwargs: List[Tuple[Value, Value]]):
        if len(args) > len(self.parameters):
            raise TypeError(
                f"Too many arguments given: "
                f"Expected {len(self.parameters)}, got {len(args)}"
            )

        for idx, value in enumerate(args):
            parameter = self.parameters[idx]
            name = parameter.name
            type = parameter.type
            if not self.validate_type(value, type):
                raise TypeError(
                    f"Invalid type for parameter {name}: "
                    f"Expected {type}, got {value.__class__.__name__}"
                )

        for key, value in kwargs:
            if not isinstance(key, Identifier):
                raise TypeError(
                    f"Invalid type for key: "
                    f"Expected Identifier, got {key.__class__.__name__}"
                )

            idx = self.index(key.value)
            if idx is None:
                keys = ", ".join(p.name for p in self.parameters)
                raise TypeError(
                    f"Unknown parameter '{key}', "
                    f"expected one of [{keys}]"
                )

            if idx < len(args):
                raise TypeError(f"Parameter '{key}' specified twice")

            parameter = self.parameters[idx]
            name = parameter.name
            type = parameter.type
            default = parameter.default
            if not self.validate_type(value, type, default=default):
                raise TypeError(
                    f"Invalid type for parameter {name}: "
                    f"Expected {type}, got {type(value)}"
                )

        for idx, (key, _) in enumerate(kwargs):
            if key in [k for k, _ in kwargs[:idx]]:
                raise TypeError(f"Duplicate key {key}")

        for parameter in self.parameters[len(args):]:
            name = parameter.name
            default = parameter.default
            if name not in [k.value for k, _ in kwargs] and default is ...:
                raise TypeError(f"Mandatory parameter '{name}' not specified")

    def format(self) -> str:
        def format_parameter(parameter: Parameter) -> str:
            if parameter.default is ...:
                return f"{parameter.name}: {parameter.type}"

            return f"{parameter.name}: {parameter.type} = {parameter.default}"

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


@dataclass
class BaseCommand(metaclass=Descriptor):
    ALIASES: ClassVar[List[str]]

    on_command: ClassVar[Any]

    ass: Assnouncer
    message: Message
    channel: MessageableChannel = None

    def __post_init__(self):
        self.channel = self.message.channel

    async def respond(self, message: str):
        await self.ass.message(message, channel=self.channel)

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
        return asspp.parse(content)

    @staticmethod
    def can_run(content: str) -> bool:
        try:
            command = BaseCommand.parse(content)
            if not isinstance(command.callable, Identifier):
                return False

            command_type = BaseCommand.find_command(command.callable)
            return command_type is not None
        except (SyntaxError, TypeError):
            return False

    @classmethod
    def accept(cls, name: Identifier) -> bool:
        return name.value in cls.ALIASES

    @staticmethod
    def find_command(name: Identifier) -> Type[BaseCommand]:
        for command_type in util.subclasses(BaseCommand):
            if command_type.accept(name):
                return command_type
        return None

    @staticmethod
    async def run(ass: Assnouncer, message: Message, expression: Expression) -> Value:
        if isinstance(expression, Null):
            return None

        if isinstance(expression, Value):
            return expression

        if not isinstance(expression, Command):
            raise TypeError("Cannot evaluate expression")

        name = await BaseCommand.run(ass, message, expression.callable)
        if not isinstance(name, Identifier):
            raise TypeError("Callable expression must result in identifier")

        command_type = BaseCommand.find_command(name)
        if command_type is None:
            return None

        logger.info(f"Running {command_type.__name__}")

        arguments = expression.arguments

        args = arguments.args
        kwargs = arguments.kwargs

        help = command_type.analyze()

        evaluated_args: List[Value] = []
        for arg in args:
            arg = await BaseCommand.run(ass, message, arg)
            evaluated_args.append(arg)

        evaluated_kwargs: List[Tuple[Value, Value]] = []
        for key, value in kwargs:
            key = await BaseCommand.run(ass, message, key)
            value = await BaseCommand.run(ass, message, value)
            evaluated_kwargs.append((key, value))

        help.validate(evaluated_args, evaluated_kwargs)

        instance = command_type(ass=ass, message=message)
        result = await instance.on_command(*evaluated_args, **{k.value: v for k, v in evaluated_kwargs})

        if result is not None and not isinstance(result, Value):
            raise TypeError("Commands must return wrapped values or None")

        return result

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

            parameter = Parameter(name=name, type=hint, default=default)
            parameters.append(parameter)

        return_type = signature.return_annotation

        return Help(
            aliases=aliases,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type
        )
