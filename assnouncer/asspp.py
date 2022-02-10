from __future__ import annotations

import ast
import regex

from regex import VERSION1
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Match, TypeVar, Type


T = TypeVar("T")


@dataclass
class ParseError(SyntaxError):
    text: str
    start: int
    stop: int


class TokenType(Enum):
    COMMA = ","
    EQUAL = "="
    OPEN_BRACE = "\\["
    CLOSE_BRACE = "\\]"
    TIMESTAMP = "-?\\d+:\\d+"
    NUMBER = "-?\\d+(?:\\.\\d+)?"
    NULL = "null"
    IDENTIFIER = "\\w+"
    STRING = "\"(?:[^\\\\\"]|(?:\\\\.))*\""
    BULLSHIT = "\\S+"


@dataclass
class Token:
    start: int
    stop: int
    text: str
    type: TokenType


@dataclass(eq=True, frozen=True)
class Expression:
    start: int = field(compare=False, hash=False)
    stop: int = field(compare=False, hash=False)

    def format(self) -> str:
        pass

    def __str__(self) -> str:
        return self.format()


@dataclass(eq=True, frozen=True)
class Value(Expression):
    @classmethod
    def new(cls: Type[T], value) -> T:
        return cls(None, None, value)

    @classmethod
    def parse(cls: Type[T], start: int, stop: int, text: str) -> T:
        pass

    def format(self) -> str:
        pass


@dataclass(eq=True, frozen=True)
class Null(Value):
    value: Type[None] = None

    @classmethod
    def parse(self, start: int, stop: int, _: str) -> Null:
        return Null(start=start, stop=stop, value=None)

    def format(self) -> str:
        return "null"
    
    def __call__(self, start: int, stop: int, value: str) -> Null:
        return Null.__class__(start, stop, value)

    def __eq__(self, other: Expression) -> bool:
        return self.__class__ is other.__class__


Null = Null.new(None)


@dataclass(eq=True, frozen=True)
class Number(Value):
    value: float

    @staticmethod
    def parse(start: int, stop: int, text: str) -> Number:
        return Number(start=start, stop=stop, value=float(text))

    def format(self) -> str:
        return str(self.value)

    def __add__(self, other: Number) -> Number:
        return Number.new(self.value + other.value)

    def __sub__(self, other: Number) -> Number:
        return Number.new(self.value - other.value)

    def __mul__(self, other: Number) -> Number:
        return Number.new(self.value * other.value)

    def __mod__(self, other: Number) -> Number:
        return Number.new(self.value % other.value)

    def __truediv__(self, other: Number) -> Number:
        return Number.new(self.value / other.value)


@dataclass(eq=True, frozen=True)
class Identifier(Value):
    value: str

    @staticmethod
    def parse(start: int, stop: int, text: str) -> Identifier:
        return Identifier(start=start, stop=stop, value=text)

    def format(self) -> str:
        return self.value

    def __add__(self, other: Identifier) -> Identifier:
        return Identifier.new(self.value + other.value)


@dataclass(eq=True, frozen=True)
class String(Value):
    value: str

    @staticmethod
    def parse(start: int, stop: int, text: str, evaluate: bool = True) -> String:
        value = ast.literal_eval(text) if evaluate else text
        return String(start=start, stop=stop, value=value)

    def format(self) -> str:
        return repr(self.value)

    def __add__(self, other: String) -> String:
        return String.new(self.value + other.value)


@dataclass(eq=True, frozen=True)
class Timestamp(Value):
    value: int
    minutes: int
    seconds: int

    @staticmethod
    def parse(start: int, stop: int, text: str) -> Timestamp:
        minutes, seconds = text.split(":")
        minutes, seconds = int(minutes), int(seconds)

        return Timestamp(
            start=start,
            stop=stop,
            value=minutes * 60 + seconds,
            minutes=minutes,
            seconds=seconds
        )

    def format(self) -> str:
        return f"{self.value // 60:02.0f}:{self.value % 60:02.0f}"


@dataclass(eq=True, frozen=True)
class Container(Expression):
    args: List[Expression] = field(default_factory=list)
    kwargs: List[Tuple[Expression, Expression]] = field(default_factory=list)

    def format(self) -> str:
        args = [f"{arg}" for arg in self.args]
        kwargs = [f"{k}={b}" for k, b in self.kwargs]
        arglist = ", ".join(args + kwargs)
        return f"[{arglist}]"


@dataclass(eq=True, frozen=True)
class Command(Expression):
    callable: Expression
    arguments: Container

    def format(self) -> str:
        return f"{self.callable}{self.arguments}"


def make_token(match: Match):
    start = match.start()
    stop = match.end()
    for key, value in match.groupdict().items():
        if value is not None:
            return Token(
                start=start,
                stop=stop,
                text=value,
                type=TokenType[key]
            )


def tokenize(text: str) -> List[Token]:
    regexes = [f"(?P<{type.name}>{type.value})" for type in TokenType]
    gigaregex = "|".join(regexes)

    return list(map(make_token, regex.finditer(gigaregex, text, flags=VERSION1)))


def find_brace(tokens: List[Token]) -> List[Token]:
    if not tokens:
        return None

    if tokens[0].type != TokenType.OPEN_BRACE:
        return None

    depth = 0

    copy = tokens.copy()
    while copy:
        token = copy.pop(0)

        if token.type is TokenType.OPEN_BRACE:
            depth += 1

        if token.type is TokenType.CLOSE_BRACE:
            depth -= 1

        if depth == 0:
            break

    idx = len(tokens) - len(copy)
    if idx == 0 or depth != 0:
        return None

    return tokens[:idx]


def parse_split(tokens: List[Token], type: TokenType) -> List[List[Token]]:
    copy = tokens.copy()
    splits = []

    split = []
    while copy:
        token = copy[0]

        if token.type is type:
            splits.append(split)
            split = []
        elif token.type is TokenType.OPEN_BRACE:
            span = find_brace(copy)
            if span is None:
                raise ParseError(
                    text="Open brace not closed",
                    start=token.start,
                    stop=token.stop
                )

            split.extend(span)

            copy = copy[len(span) - 1:]
        else:
            split.append(token)

        copy.pop(0)

    if split:
        splits.append(split)

    return splits


def parse_primitive(tokens: List[Token]) -> Value:
    if len(tokens) != 1:
        return None

    map: Dict[TokenType, Type[Value]] = {
        TokenType.IDENTIFIER: Identifier,
        TokenType.NUMBER: Number,
        TokenType.STRING: String,
        TokenType.TIMESTAMP: Timestamp,
        TokenType.NULL: Null
    }

    first = tokens[0]
    if first.type in map:
        return map[first.type].parse(first.start, first.stop, first.text)


def parse_kwarg(tokens: List[Token]) -> Tuple[str, Value]:
    if not tokens:
        return None

    splits = parse_split(tokens, TokenType.EQUAL)
    if len(splits) != 2:
        return None

    k, v = splits

    key = parse_expression(k)
    value = parse_expression(v)
    if None not in (key, value):
        return key, value


def parse_container(tokens: List[Token]) -> Container:
    first = tokens[0]
    last = tokens[-1]

    arglist_tokens = tokens[1:-1]
    splits = parse_split(arglist_tokens, TokenType.COMMA)

    args = [arg for arg in map(parse_expression, splits) if arg is not None]
    kwargs = [kwarg for kwarg in map(parse_kwarg, splits) if kwarg is not None]

    idx = 0
    for split, arg, kwarg in zip(splits, args, kwargs):
        if not split:
            first = split[0]
            last = split[-1]
            raise ParseError(
                text="Command argument could not be parsed",
                start=first.start,
                stop=last.stop
            )

        if arg is None or kwarg is None:
            first = split[0]
            last = split[-1]
            raise ParseError(
                text="Command argument could not be parsed",
                start=first.start,
                stop=last.stop
            )

        idx += len(split) + 1

    if len(args) + len(kwargs) != len(splits):
        raise SyntaxError("Could not parse all arguments")

    return Container(start=first.start, stop=last.stop, args=args, kwargs=kwargs)


def parse_expression(tokens: List[Token]) -> Expression:
    if not tokens:
        return None

    first = tokens[0]
    if len(tokens) == 1:
        return parse_primitive([first])

    tokens = tokens[1:]

    callable = parse_primitive([first])
    while tokens and tokens[0].type is TokenType.OPEN_BRACE:
        arglist = find_brace(tokens)
        if arglist is None:
            raise SyntaxError("Open brace not closed")
        arguments = parse_container(arglist)
        start = callable.start
        stop = arguments.stop
        callable = Command(
            start=start,
            stop=stop,
            callable=callable,
            arguments=arguments
        )
        tokens = tokens[len(arglist):]

    if not tokens:
        return callable


def parse(text: str) -> Command:
    tokens = tokenize(text)

    if not tokens:
        raise SyntaxError("Empty input")

    if len(tokens) > 1 and tokens[1].type is TokenType.OPEN_BRACE:
        tokens = tokens[:1] + find_brace(tokens[1:])
    else:
        tokens = tokens[:1]

    callable: Command = parse_expression(tokens)
    if not isinstance(callable, (Identifier, Command)):
        raise SyntaxError(f"Expected Identifer")

    start = callable.start
    stop = callable.stop
    if isinstance(callable, Identifier):
        arguments = Container(start=start, stop=stop)
        callable = Command(
            start=start,
            stop=stop,
            callable=callable,
            arguments=arguments
        )

    payload = text[stop:].strip()
    if payload:
        callable.arguments.kwargs.append((
            Identifier.parse(stop, stop, "payload"),
            String.parse(stop, len(text), payload, evaluate=False)
        ))

    return callable
