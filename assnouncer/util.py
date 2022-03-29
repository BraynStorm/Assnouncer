from __future__ import annotations

import hashlib
from tempfile import TemporaryDirectory

from assnouncer.config import THEMES_DIR, FFMPEG_PATH, DOWNLOAD_DIR
from assnouncer.asspp import Timestamp, Number, Null
from assnouncer.downloaders import BaseDownloader

from dataclasses import dataclass
from typing import List, TypeVar, Union
from pytube import YouTube, Search
from pathlib import Path
from discord import FFmpegOpusAudio, Member

T = TypeVar("T", bound="type")


@dataclass
class SongRequest:
    where: TemporaryDirectory
    source: FFmpegOpusAudio
    query: str
    uri: str
    start: Union[Timestamp, Number] = Null
    stop: Union[Timestamp, Number] = Null


def subclasses(cls: T) -> List[T]:
    subclasses = []

    queue = [cls]
    while queue:
        current_class = queue.pop()
        for child in current_class.__subclasses__():
            if child not in subclasses:
                subclasses.append(child)
                queue.append(child)

    return subclasses


def get_theme_path(user: Member) -> Path:
    return (THEMES_DIR / f"{user.name}#{user.discriminator}").with_suffix(".opus")


def get_download_path(
    uri: str,
    start: Union[Timestamp, Number] = Null,
    stop: Union[Timestamp, Number] = Null,
) -> Path:
    if start != Null:
        start = round(start)

    if stop != Null:
        stop = round(stop)

    hash_string = f"[{start}-{stop}] {uri}"
    hash_value = hashlib.md5(hash_string.encode("utf8")).hexdigest()
    return (DOWNLOAD_DIR / hash_value).with_suffix(".opus")


def search_song(query: str) -> str:
    results: List[YouTube]
    results, _ = Search(query).fetch_and_parse()
    if results:
        return results[0].watch_url
    else:
        print(f"[warn] Not Youtube results for {repr(query)}")

    return None


def can_download(uri: str) -> bool:
    return any(d.accept(uri) for d in subclasses(BaseDownloader))


def resolve_uri(query: str) -> str:
    if can_download(query):
        return query
    else:
        return search_song(query)


async def load_source(uri: Path) -> FFmpegOpusAudio:
    if not uri.is_file():
        return None

    return await FFmpegOpusAudio.from_probe(
        source=str(uri),
        executable=str(FFMPEG_PATH)
    )


async def download(
    query: str,
    start: Union[Timestamp, Number] = Null,
    stop: Union[Timestamp, Number] = Null,
    download_path: Path = None,
    force: bool = False
) -> SongRequest:
    uri = resolve_uri(query)
    if uri is None:
        print("[warn] Requested song could not be found or is not supported")
        return None

    where = TemporaryDirectory()

    if download_path is None:
        download_path = get_download_path(uri, start=start, stop=stop)

    async def load_song() -> SongRequest:
        load_path = Path(where.name) / "bingchillin.opus"
        load_path.write_bytes(download_path.read_bytes())
        source = await load_source(load_path)
        return SongRequest(
            where=where,
            source=source,
            query=query,
            uri=uri,
            start=start,
            stop=stop
        )

    if download_path.is_file():
        if force:
            download_path.unlink()
        else:
            return await load_song()

    for downloader in subclasses(BaseDownloader):
        if downloader.accept(uri):
            print(f"[info] Downloading via {downloader.__name__}")
            if downloader.download(uri, download_path, start=start, stop=stop):
                print("[info] Download successful")
                return await load_song()
            else:
                print("[warn] Download unsuccessful")

    return None
