from __future__ import annotations

import ast
import regex

from regex import VERSION1
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple, Match, TypeVar, Type

T = TypeVar("T")


class TokenType(Enum):
    COMMA = ","
    EQUAL = "="
    OPEN_BRACE = "\\["
    CLOSE_BRACE = "\\]"
    TIMESTAMP = "\\d+:\\d+"
    NUMBER = "\\d+(?:\\.\\d+)?"
    IDENTIFIER = "\\w+"
    STRING = "\"(?:[^\\\\\"]|(?:\\\\.))*\""
    BULLSHIT = "\\S+"


@dataclass(unsafe_hash=True)
class Token:
    start: int
    stop: int
    text: str
    type: TokenType


@dataclass(unsafe_hash=True)
class Value:
    text: str

    @classmethod
    def parse(cls: T, text: str) -> T:
        pass


@dataclass(unsafe_hash=True)
class Number(Value):
    value: float

    @staticmethod
    def parse(text: str) -> Number:
        return Number(
            value=float(text),
            text=text
        )


@dataclass(unsafe_hash=True)
class Identifier(Value):
    value: str

    @staticmethod
    def parse(text: str) -> Identifier:
        return Identifier(
            value=text,
            text=text
        )


@dataclass(unsafe_hash=True)
class String(Value):
    value: str

    @staticmethod
    def parse(text: str, unescape: bool = True) -> String:
        value = ast.literal_eval(text) if unescape else text
        return String(
            value=value,
            text=text
        )


@dataclass(unsafe_hash=True)
class Timestamp(Value):
    value: int
    minutes: int
    seconds: int

    @staticmethod
    def parse(text: str) -> Timestamp:
        minutes, seconds = text.split(":")
        minutes, seconds = int(minutes), int(seconds)

        return Timestamp(
            value=minutes * 60 + seconds,
            minutes=minutes,
            seconds=seconds,
            text=text
        )


@dataclass
class Command:
    name: str
    args: List[Value]
    kwargs: Dict[str, Value]
    payload: str = None


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


def find(tokens: List[Token], type: TokenType) -> int:
    copy = tokens.copy()
    while copy and copy[0].type is not type:
        copy.pop(0)

    idx = len(tokens) - len(copy)
    if idx == 0:
        return None

    return idx


def parse_split(tokens: List[Token], separator: TokenType) -> List[List[Token]]:
    splits = []

    split = []
    while tokens:
        token = tokens.pop(0)

        if token.type is separator:
            splits.append(split)
            split = []
        else:
            split.append(token)

    if split:
        splits.append(split)

    return splits


def parse_arg(tokens: List[Token]) -> Value:
    if len(tokens) != 1:
        return None

    map: Dict[TokenType, Type[Value]] = {
        TokenType.IDENTIFIER: Identifier,
        TokenType.NUMBER: Number,
        TokenType.STRING: String,
        TokenType.TIMESTAMP: Timestamp
    }

    first, = tokens
    if first.type in map:
        return map[first.type].parse(first.text)


def parse_kwarg(tokens: List[Token]) -> Tuple[str, Value]:
    if len(tokens) != 3:
        return None

    first, second, third = tokens
    if first.type is not TokenType.IDENTIFIER:
        return None

    if second.type is not TokenType.EQUAL:
        return None

    key = Identifier.parse(first.text).value
    value = parse_arg([third])
    if value is not None:
        return key, value


def parse(text: str) -> Command:
    tokens = tokenize(text)

    if not tokens:
        raise SyntaxError("Empty input")

    first = tokens[0]
    if first.type is not TokenType.IDENTIFIER:
        raise SyntaxError("Expected name")

    name = Identifier.parse(first.text).value

    args = None
    kwargs = None

    tokens = tokens[1:]
    if tokens:
        first = tokens[0]
        if first.type is TokenType.OPEN_BRACE:
            idx = find(tokens, TokenType.CLOSE_BRACE)

            if idx is None:
                raise SyntaxError("Expected closing brace")

            arglist_tokens = tokens[1:idx]
            splits = parse_split(arglist_tokens, TokenType.COMMA)

            args = [arg for arg in map(parse_arg, splits) if arg]
            kwargs = [kwarg for kwarg in map(parse_kwarg, splits) if kwarg]

            if len(args) + len(kwargs) != len(splits):
                raise SyntaxError("Could not parse all arguments")

            keys = {k for k, _ in kwargs}

            if len(keys) != len(kwargs):
                raise SyntaxError("Duplicate kwargs")

            kwargs = {k: v for k, v in kwargs}

            tokens = tokens[idx + 1:]

    payload = None
    if tokens:
        payload = text[tokens[0].start:]

    return Command(name=name, args=args, kwargs=kwargs, payload=payload)
