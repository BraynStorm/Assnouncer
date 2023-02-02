from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import cast
from assnouncer import config

import pickle
import json


@dataclass(frozen=True)
class Play:
    url: str
    played_on: datetime
    request_text: str | None = None
    queued_on: datetime | None = None
    queued_by: str | None = None
    start: float | None = None
    stop: float | None = None


@dataclass(frozen=True)
class Stats:
    plays: list[Play] = field(default_factory=list)


def on_play_song(play: Play):
    stats: Stats

    STATS_PICKLE_PATH = Path(f"asstats-{config.GUILD_ID}.pickle")
    STATS_JSON_PATH = Path(f"asstats-{config.GUILD_ID}.json")

    if not STATS_PICKLE_PATH.exists():
        stats = Stats()
    else:
        with STATS_PICKLE_PATH.open("rb") as stats_file:
            stats = cast(Stats, pickle.load(stats_file))

    stats.plays.append(play)

    with STATS_PICKLE_PATH.open("wb") as stats_file:
        pickle.dump(stats, stats_file)

    stats_dict = asdict(stats)
    for play in stats_dict["plays"]:
        if play["played_on"] is not None:
            play["played_on"] = play["played_on"].timestamp()
        if play["queued_on"] is not None:
            play["queued_on"] = play["queued_on"].timestamp()

    with STATS_JSON_PATH.open("w", newline="\n", encoding="utf-8") as stats_file:
        json.dump(stats_dict, stats_file)
