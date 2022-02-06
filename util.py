from __future__ import annotations

import hashlib

from config import THEMES_DIR, FFMPEG_PATH, DOWNLOAD_DIR

from commandline import Timestamp
from dataclasses import dataclass
from typing import List
from pytube import YouTube, Search
from pathlib import Path
from discord import FFmpegOpusAudio, Member
from downloaders import BaseDownloader


@dataclass
class LoadedSong:
    uri: str
    source: FFmpegOpusAudio


@dataclass
class SongRequest:
    query: str
    start: Timestamp = None
    stop: Timestamp = None


def get_theme_path(user: Member) -> Path:
    return (THEMES_DIR / f"{user.name}#{user.discriminator}").with_suffix(".ogg")


def get_download_path(request: SongRequest) -> Path:
    hash_value = hashlib.md5(str(request).encode("utf8")).hexdigest()
    return (DOWNLOAD_DIR / hash_value).with_suffix(".ogg")


def search_song(query: str) -> str:
    results: List[YouTube]
    results, _ = Search(query).fetch_and_parse()
    if results:
        return results[0].watch_url


def can_download(uri: str):
    return any(d.accept(uri) for d in BaseDownloader.get_instances())


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


async def download(request: SongRequest, filename: Path = None, force: bool = False):
    uri = resolve_uri(request.query)
    if uri is None or not can_download(uri):
        print("[warn] Requested song could not be found or is not supported")
        return None

    if filename is None:
        filename = get_download_path(request)

    async def load_song():
        source = await load_source(filename)
        return LoadedSong(uri=uri, source=source)

    if filename.is_file() and not force:
        return await load_song()

    for downloader in BaseDownloader.get_instances():
        if downloader.accept(uri):
            print(f"[info] Downloading via {downloader.__name__}")
            if downloader.download(uri, filename, start=request.start, stop=request.stop):
                break

    return await load_song()
