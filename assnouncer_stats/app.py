import pickle
import requests
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from flask import Flask, Response

from assnouncer.stats import Play, Stats

requests.packages.urllib3.util.connection.HAS_IPV6 = False


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


YOUTUBE_API_KEY = Path("youtube-api-key.txt").read_text().strip()


@dataclass(frozen=True)
class CountedPlay:
    url: str
    count: int


def url_normalize(url: str) -> str:
    return url.replace("https://www.", "https://")


def stats_json_string(server: int) -> str:
    with open(f"./asstats-{server}.json", "r") as file:
        return file.read()


def stats(server: int) -> "Stats":
    with open(f"./asstats-{server}.pickle", "rb") as file:
        stats = pickle.load(file)
        assert isinstance(stats, Stats)
        return Stats(
            list(filter(lambda play: "'s theme" not in play.request_text, stats.plays))
        )


def group_by_url(plays: list[Play]) -> dict[str, list[Play]]:
    group_by_url: dict[str, list[Play]] = defaultdict(list)
    for play in plays:
        if "'s theme" not in play.request_text:
            url = url_normalize(play.url)
            group_by_url[url].append(play)

    return group_by_url


def group_by_url_by_plays(plays: list[Play]) -> list[tuple[int, list[Play]]]:
    by_url = group_by_url(plays)

    grouped = list(zip(map(len, by_url.values()), by_url.values()))
    grouped.sort(key=lambda k: k[0], reverse=True)
    return grouped


def oldest_plays_for_urls(plays: list[Play]) -> list[Play]:
    by_url = group_by_url(plays)

    newest_play_for_url = [
        max(plays, key=lambda play: play.queued_on) for plays in by_url.values()
    ]
    newest_play_for_url.sort(key=lambda k: k.queued_on)
    return newest_play_for_url


def all_players(plays: list[Play]) -> set[str]:
    return {play.queued_by for play in plays}


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

    urls = [url_normalize(record.url) for record in filtered_records]
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


def video_title(url: str, use_cache=True) -> str:
    response_json = None

    if use_cache:
        cache: dict[str, Any]
        p = Path("youtube-api-cache.pickle")
        if p.exists():
            cache = pickle.loads(p.read_bytes())
        else:
            cache = dict()

        try:
            response_json = cache[url]
        except KeyError:
            pass

    if response_json is None:
        vid_id = video_id(url)
        api_url = (
            "https://youtube.googleapis.com/youtube/v3/videos?part=snippet"
            f"&id={vid_id}&key={YOUTUBE_API_KEY}"
        )

        # Retry 2 times
        for _ in range(3):
            r = requests.get(api_url, timeout=1)
            response_json = r.json()
            if r.status_code != 200:
                print("Youtube API limit hit.", r.content.decode("utf-8"))
                if r.status_code == 403:
                    import time

                    time.sleep(0.3)
                return ""

        if use_cache:
            cache[url] = response_json
            p.write_bytes(pickle.dumps(cache))

    try:
        return response_json["items"][0]["snippet"]["title"]
    except:
        print(f"No title for {url} - {response_json['items']}")
        return "<blocked>"


def get_all_servers() -> list[int]:
    return [
        int(file_path.stem.removeprefix("asstats-"))
        for file_path in Path(".").glob("asstats-*.pickle")
    ]


def get_server() -> int:
    import os

    server = os.environ.get("SERVER", None)
    if server:
        return int(server)
    else:
        return get_all_servers()[0]


def define_routes():
    from flask import redirect, render_template

    @app.route("/<int:server>/", methods=["GET"])
    def root(server):
        return redirect(f"/{server}/ui")

    @app.route("/<int:server>/ui", methods=["GET"])
    def ui_index(server: int):
        records = stats(server).plays
        themes = [record for record in records if "'s theme" in record.request_text]
        records = [
            record for record in records if "'s theme" not in record.request_text
        ]
        # NOTE(bozho2):
        #   After Discord updated the user format, now the users don't have the #XXXX suffix.
        #   So Assnouncer just puts #0 at the ends of the usernames.
        #   It's fugly to display it so we remove it
        users = {
            record.queued_by for record in records if record.queued_by.endswith("#0")
        }

        grouped_records = group_by_url_by_plays(records)

        return render_template(
            "index.jinja",
            server=server,
            themes=themes,
            records=records,
            users=users,
            grouped_records=grouped_records,
            len=len,
            **globals(),
        )

    @app.route("/<int:server>/ui/all", methods=["GET"])
    def ui_all(server: int):
        records = [
            record
            for record in stats(server).plays
            if "'s theme" not in record.request_text
        ]
        return render_template(
            "all.jinja",
            server=server,
            records=records,
            len=len,
            **globals(),
        )

    @app.route("/<int:server>/ui/blast", methods=["GET"])
    def ui_blast(server):
        records = stats(server).plays
        oldest_plays = oldest_plays_for_urls(records)
        return render_template(
            "blast.jinja",
            server=server,
            oldest_plays=oldest_plays,
            **globals(),
        )

    @app.route("/v1/stats/<int:server>/raw")
    def v1_stats_server_raw(server: int):
        server = int(server)
        return Response(
            stats_json_string(server), 200, headers={"Content-Type": "application/json"}
        )

    @app.route("/v1/stats/<int:server>/top_n/<string:filter>", defaults=dict(top_n=10))
    @app.route("/v1/stats/<int:server>/top_n/<string:filter>/<int:top_n>")
    def v1_stats_server_top_n(server: int, filter: str, top_n: int):
        server = int(server)
        s = stats(server)
        results = top_n_urls(s.plays, top_n, filter)
        return results


define_routes()
