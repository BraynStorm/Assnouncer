import pickle
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from flask import Flask, Response

from assnouncer.stats import Play, Stats

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


@dataclass(frozen=True)
class CountedPlay:
    play: Play
    count: int


def stats_json_string(server: int) -> str:
    with open(f"../asstats-{server}.json", "r") as file:
        return file.read()


def stats(server: int) -> "Stats":
    with open(f"../asstats-{server}.pickle", "rb") as file:
        stats = pickle.load(file)
        assert isinstance(stats, Stats)
        return stats


def group_by_url(plays: list[Play]) -> list[tuple[int, list[Play]]]:
    from collections import defaultdict

    group_by_url: dict[str, list[Play]] = defaultdict(list)
    for play in plays:
        if "'s theme" not in play.request_text:
            group_by_url[play.url].append(play)

    grouped = list(zip(map(len, group_by_url.values()), group_by_url.values()))
    grouped.sort(key=lambda k: k[0], reverse=True)
    return grouped


def all_players(plays: list[Play]) -> set[str]:
    return {play.queued_by for play in plays}


def counted_players(plays: list[Play]) -> list[CountedPlay]:
    c = Counter([play.queued_by for play in plays])
    return list(map(CountedPlay, c.most_common(None)))


def filter_this_month(play: Play):
    now = datetime.now()
    played_on = play.played_on
    return played_on.year == now.year and played_on.month == now.month


def filter_last_month(play: Play):
    now = datetime.now()
    last_month = datetime(now.year, now.month - 1, 1)
    played_on = play.played_on
    return played_on.year == last_month.year and played_on.month == last_month.month


def filter_today(play: Play):
    now = datetime.now()
    played_on = play.played_on
    return (
        played_on.year == now.year
        and played_on.month == now.month
        and played_on.day == now.day
    )


def filter_any(play: Play) -> bool:
    return True


def second_element(x):
    return x[1]


def filter_user_this_month(record: Play, user: str) -> bool:
    now = datetime.now()
    played_on = record.played_on
    return (
        played_on.year == now.year
        and played_on.month == now.month
        and record.queued_by == user
    )


def filter_user_last_month(record: Play, user: str) -> bool:
    now = datetime.now()
    last_month = datetime(now.year, now.month - 1, 1)
    played_on = record.played_on
    return (
        played_on.year == last_month.year
        and played_on.month == last_month.month
        and record.queued_by == user
    )


def get_filter(
    filter: Callable[[Play], bool] | str | None = None,
    *args,
) -> Callable[[Play], bool]:
    if isinstance(filter, str):
        filter = "filter_" + filter
        filter_func = globals()[filter]
        assert callable(filter_func)
    elif callable(filter):
        filter_func = filter
    else:
        filter_func = filter_any

    return filter_func


def plays_by_user(
    records: list[Play], filter: Callable[[Play], bool] | str | None
) -> list[tuple[str, int]]:
    import builtins

    records = builtins.filter(get_filter(filter), records)
    c = Counter([record.queued_by for record in records])
    return c.most_common(None)


def top_n_urls(
    records: list[Play],
    n: int = 10,
    filter: str | Callable[[Play], bool] | None = None,
    *args,
) -> list[tuple[str, int]]:
    import builtins

    filter_func = get_filter(filter, *args)
    filtered_records = builtins.filter(lambda x: filter_func(x, *args), records)

    urls = [record.url for record in filtered_records]
    counts = Counter(urls)
    return sorted(counts.most_common(n), key=second_element, reverse=True)


def unique_play_texts(records: list[Play]) -> list[tuple[str, int]]:
    counts = Counter([record.request_text for record in records])
    return list(sorted(counts.most_common(None), key=second_element, reverse=True))


def unique_players(records: list[Play]) -> list[tuple[str, int]]:
    counts = Counter([record.queued_by for record in records])
    return list(sorted(counts.most_common(None), key=second_element, reverse=True))


def video_id(url: str) -> str:
    try:
        return url[url.index("=") + 1 :]
    except:
        return url[url.index("/") + 1 :]


def define_routes():
    from flask import redirect, render_template

    @app.route("/", methods=["GET"])
    def root():
        return redirect("/ui")

    @app.route("/ui", methods=["GET"])
    def ui_index():
        servers = [
            int(file_path.stem.removeprefix("asstats-"))
            for file_path in Path("..").glob("asstats-*.pickle")
        ]
        records = stats(servers[0]).plays
        themes = [record for record in records if "'s theme" in record.request_text]
        records = [
            record for record in records if "'s theme" not in record.request_text
        ]
        users = {record.queued_by for record in records}

        grouped_records = group_by_url(records)

        return render_template(
            "index.jinja",
            servers=servers,
            themes=themes,
            records=records,
            users=users,
            grouped_records=grouped_records,
            len=len,
            **globals(),
        )

    @app.route("/ui/all", methods=["GET"])
    def ui_all():
        servers = [
            int(file_path.stem.removeprefix("asstats-"))
            for file_path in Path("..").glob("asstats-*.pickle")
        ]
        records = [
            record
            for record in stats(servers[0]).plays
            if "'s theme" not in record.request_text
        ]
        return render_template(
            "all.jinja",
            records=records,
            len=len,
            **globals(),
        )

    @app.route("/v1/stats/<int:server>/raw")
    def v1_stats_server_raw(server: int):
        server = int(server)
        return Response(
            stats_json_string(server), 200, headers={"Content-Type": "application/json"}
        )


define_routes()
