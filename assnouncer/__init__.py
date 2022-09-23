import logging

from assnouncer import downloaders
from assnouncer import commands
from assnouncer import audio

from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL, StreamHandler, Formatter
from typing import Any
from discord import utils


class ColourFormatter(Formatter):
    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = [
        (DEBUG, '\x1b[40;1m'),
        (INFO, '\x1b[34;1m'),
        (WARNING, '\x1b[38;5;202m'),
        (ERROR, '\x1b[31m'),
        (CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: Formatter(
            f'\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[35m%(name)-24s\x1b[0m %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


utils.setup_logging = lambda **_: None

handler = StreamHandler()

formatter: Any
if utils.stream_supports_colour(handler.stream):
    formatter = ColourFormatter()
else:
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = Formatter('[{asctime}] [{levelname:<8}] {name:<32}: {message}', dt_fmt, style='{')

logger = logging.getLogger()

handler.setFormatter(formatter)
logger.setLevel(INFO)
logger.addHandler(handler)
