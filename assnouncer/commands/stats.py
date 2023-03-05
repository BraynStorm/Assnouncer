from __future__ import annotations

import logging
import requests

from assnouncer import util
from assnouncer.asspp import String, Timestamp
from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, ClassVar, cast

logger = logging.getLogger(__name__)


class Filter:
    this_month = "this_month"
    last_month = "last_month"
    user_this_month = "user_this_month"
    user_last_month = "user_last_month"


def url_stats(filter: str, n: int = None) -> str:
    from assnouncer.config import GUILD_ID

    if not n:
        n = 10
    return f"/v1/stats/{GUILD_ID}/top_n/{filter}/{n}"


@dataclass
class Stats(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["stats"]

    async def on_command(self, payload: String = None):
        """
        Sends a message, containing the address of the statistics page for this
        Assnouncer instance.
        """

        if payload == "my":
            pass

        n = 10
        filter = Filter.this_month

        response = requests.get("http://ifconfig.me/ip")
        base_url = f"http://{response.text}:8010"
        stats_url = base_url + url_stats(filter=filter, n=n)
        ui_url = f"{base_url}/ui"

        stats_response = requests.get(stats_url)
        stats = cast(list[str], stats_response.json())

        from yt_dlp import YoutubeDL

        with YoutubeDL() as yt:
            top_n = "\n".join(
                map(
                    lambda t: f"#{t[0]} - "
                    + yt.extract_info(t[1][0], download=False).get("title", "Unknown"),
                    enumerate(stats, start=1),
                )
            )
        if stats_response.status_code == 200:
            await self.respond(f"{ui_url}\n\nThis month's top 10:\n```{top_n}```")
        else:
            logger.info(f"Stats were not available. {stats_response}")
            await self.respond(f"{ui_url}\n\nStats are not available!")
