from flask import Flask, Response
from dataclasses import dataclass
from pathlib import Path
from assnouncer.stats import Play, Stats

import pickle


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


@dataclass
class RankedPlays:
    top_song_today: Play


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


def unique_play_texts(records: list[Play]) -> list[str]:
    return records


def video_id(url: str) -> str:
    try:
        return url[url.index("=") + 1 :]
    except:
        return url[url.index("/") + 1 :]


def define_routes():
    from flask import render_template, redirect

    @app.route("/", methods=["GET"])
    def root():
        return redirect("/ui")

    @app.route("/ui", methods=["GET"])
    def ui_index():
        servers = [
            int(file_path.stem.removeprefix("asstats-"))
            for file_path in Path("..").glob("asstats-*.pickle")
        ]

        return render_template("index.jinja", servers=servers, len=len, **globals())

    @app.route("/v1/stats/<int:server>/raw")
    def v1_stats_server_raw(server: int):
        server = int(server)
        return Response(
            stats_json_string(server), 200, headers={"Content-Type": "application/json"}
        )


define_routes()
