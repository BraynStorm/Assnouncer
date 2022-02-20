from __future__ import annotations

import inspect

from assnouncer import asspp
from assnouncer import util
from assnouncer.asspp import Command, Timestamp, String, Identifier, Number, Null, Value, Expression
from assnouncer.metaclass import Descriptor

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, List, Tuple, Type, TypeVar
from discord import Message, TextChannel

if TYPE_CHECKING:
    from assnouncer.assnouncer import Assnouncer


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

    def validate(self, args: List[Value], kwargs: List[Tuple[Expression, Expression]]):
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
                    f"Expected Identifier, got {key.__class.__name__}"
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

    ass: Assnouncer
    message: Message
    channel: TextChannel = None

    def __post_init__(self):
        self.channel = self.message.channel

    def respond(self, message: str):
        self.ass.message(message, channel=self.channel)

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
        except (SyntaxError, TypeError) as e:
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
    async def run(ass: Assnouncer, message: Message, expression: Expression):
        if isinstance(expression, Value):
            return expression

        if not isinstance(expression, Command):
            raise TypeError("Cannot evaluate expression")

        name = await BaseCommand.run(ass, message, expression.callable)
        if not isinstance(name, Identifier):
            raise TypeError("Callable experssion must result in identifier")

        command_type = BaseCommand.find_command(name)
        if command_type is None:
            return Null

        print(f"[info] Running {command_type.__name__}")

        arguments = expression.arguments

        args = arguments.args
        kwargs = arguments.kwargs

        help = command_type.analyze()

        for idx, arg in enumerate(args):
            args[idx] = await BaseCommand.run(ass, message, arg)

        for idx, (key, value) in enumerate(kwargs):
            key = await BaseCommand.run(ass, message, key)
            value = await BaseCommand.run(ass, message, value)
            kwargs[idx] = key, value

        help.validate(args, kwargs)

        instance = command_type(ass=ass, message=message)
        result = await instance.on_command(*args, **{k.value: v for k, v in kwargs})
        if result is None:
            result = Null

        if not isinstance(result, Expression):
            raise TypeError("Commands must return wrapped values")

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

    async def on_command(self, *args, **kwargs):
        pass
