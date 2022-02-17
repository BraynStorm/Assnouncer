from __future__ import annotations

import ast
import math
import regex

from regex import VERSION1
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Match, TypeVar, Type, Generic


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
    STRING = "(?P<q>(\"\"\"|\'\'\'|\"|\'))(?:\\\\.|[^\\\\])*?(?P=q)"
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


U = TypeVar("U", bound="Value")


@dataclass(eq=True, order=True, frozen=True)
class Value(Expression, Generic[T]):
    value: T

    @classmethod
    def new(cls: Type[U], value: T) -> U:
        return cls(None, None, value)

    @classmethod
    def parse(cls: Type[U], start: int, stop: int, text: str) -> U:
        pass


class Dummy(type):
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Expression):
            return NotImplemented

        return self is other or isinstance(other, self)

    @property
    def __class__(self):
        return Expression

    @__class__.setter
    def __class__(self, _):
        pass


@dataclass(eq=True, order=True, frozen=True)
class Null(Value[Type[None]], metaclass=Dummy):
    @classmethod
    def parse(cls, start: int, stop: int, _: str) -> Null:
        return cls(start=start, stop=stop, value=None)

    def __repr__(self) -> str:
        return "null"


@dataclass(eq=True, order=True, frozen=True)
class Number(Value[float]):
    @staticmethod
    def parse(start: int, stop: int, text: str) -> Number:
        return Number(start=start, stop=stop, value=float(text))

    def __repr__(self) -> str:
        return repr(self.value)

    def __round__(self: Number, ndigits: int = None) -> Number:
        return self.new(round(self.value, ndigits=ndigits))

    def __floor__(self: Number) -> Number:
        return self.new(math.floor(self.value))

    def __ceil__(self: Number) -> Number:
        return self.new(math.ceil(self.value))

    def __add__(self: Number, other: Number) -> Number:
        return self.new(self.value + other.value)

    def __sub__(self: Number, other: Number) -> Number:
        return self.new(self.value - other.value)

    def __mul__(self: Number, other: Number) -> Number:
        return self.new(self.value * other.value)

    def __mod__(self: Number, other: Number) -> Number:
        return self.new(self.value % other.value)

    def __truediv__(self: Number, other: Number) -> Number:
        return self.new(self.value // other.value)


@dataclass(eq=True, order=True, frozen=True)
class Identifier(Value[str]):
    @staticmethod
    def parse(start: int, stop: int, text: str) -> Identifier:
        return Identifier(start=start, stop=stop, value=text)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return repr(self.value)

    def __add__(self: Identifier, other: Identifier) -> Identifier:
        return self.new(self.value + other.value)


@dataclass(eq=True, order=True, frozen=True)
class String(Value[str]):
    @staticmethod
    def parse(start: int, stop: int, text: str, evaluate: bool = True) -> String:
        value = ast.literal_eval(text) if evaluate else text
        return String(start=start, stop=stop, value=value)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return repr(self.value)

    def __add__(self: String, other: String) -> String:
        return self.new(self.value + other.value)


@dataclass(eq=True, order=True, frozen=True)
class Timestamp(Value[int]):
    @staticmethod
    def parse(start: int, stop: int, text: str) -> Timestamp:
        minutes, seconds = text.split(":")
        return Timestamp(
            start=start,
            stop=stop,
            value=int(minutes) * 60 + int(seconds)
        )

    def __repr__(self) -> str:
        return f"{self.value // 60:02.0f}:{self.value % 60:02.0f}"

    def __add__(self: Timestamp, other: Timestamp) -> Timestamp:
        return self.new(self.value + other.value)

    def __sub__(self: Timestamp, other: Timestamp) -> Timestamp:
        return self.new(self.value - other.value)


@dataclass(eq=True, order=True, frozen=True)
class Container(Expression):
    args: List[Expression] = field(default_factory=list)
    kwargs: List[Tuple[Expression, Expression]] = field(default_factory=list)

    def __repr__(self) -> str:
        args = [f"{arg}" for arg in self.args]
        kwargs = [f"{k}={b!r}" for k, b in self.kwargs]
        arglist = ", ".join(args + kwargs)
        return f"[{arglist}]"


@dataclass(eq=True, order=True, frozen=True)
class Command(Expression):
    callable: Expression
    arguments: Container

    def __repr__(self) -> str:
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

    split: List[Token] = []
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

    return None


def parse_kwarg(tokens: List[Token]) -> Tuple[Expression, Expression]:
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

    return None


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

    callable: Expression = parse_primitive([first])
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

    return None


def parse(text: str) -> Command:
    tokens = tokenize(text)

    if not tokens:
        raise SyntaxError("Empty input")

    if len(tokens) > 1 and tokens[1].type is TokenType.OPEN_BRACE:
        tokens = tokens[:1] + find_brace(tokens[1:])
    else:
        tokens = tokens[:1]

    callable: Expression = parse_expression(tokens)
    if not isinstance(callable, (Identifier, Command)):
        raise SyntaxError("Expected Identifer")

    start: int = callable.start
    stop: int = callable.stop
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
