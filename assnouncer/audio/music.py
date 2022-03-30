from __future__ import annotations

import time

from assnouncer.config import FFMPEG_PATH

from typing import Callable, Union
from enum import IntEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from discord.opus import Encoder
from discord import FFmpegOpusAudio, VoiceClient

OPUS_DELAY = Encoder.FRAME_LENGTH / 1000.0


class MusicState(IntEnum):
    INTERRUPTED = 0
    STOPPED = 1
    CONTINUED = 2


class AudioSource(FFmpegOpusAudio):
    where: TemporaryDirectory

    def __init__(self, source: str, *, where: TemporaryDirectory, **kwargs):
        super().__init__(source, **kwargs)

        self.where = where

    @classmethod
    async def from_probe(cls, source_path: Path, **kwargs):
        where = TemporaryDirectory()
        load_path = Path(where.name) / "bingchillin.opus"
        load_path.write_bytes(source_path.read_bytes())

        return await super().from_probe(
            source=str(load_path),
            executable=str(FFMPEG_PATH),
            where=where,
            **kwargs
        )


def play(
    client: VoiceClient,
    source: AudioSource,
    callback: Callable[[], MusicState] = None
):
    if not client._connected.is_set():
        raise ValueError("Not connected to voice.")

    if not client.encoder and not source.is_opus():
        client.encoder = Encoder()

    loops: int = None
    time_start: float = None

    def reset():
        nonlocal loops
        nonlocal time_start

        loops = 0
        time_start = time.perf_counter()

    reset()

    while True:
        while not client.is_connected():
            time.sleep(0.1)
            reset()

        data = source.read()
        if not data:
            break

        loops += 1

        client.send_audio_packet(data, encode=not source.is_opus())

        if callback is not None:
            result = callback()
            if result is MusicState.STOPPED:
                break

            if result is MusicState.INTERRUPTED:
                reset()
                continue

        time_next = time_start + OPUS_DELAY * loops
        delay = max(0, OPUS_DELAY + (time_next - time.perf_counter()))

        time.sleep(delay)
