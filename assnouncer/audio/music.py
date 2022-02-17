from __future__ import annotations
import asyncio

import time

from dataclasses import dataclass
from typing import Callable
from enum import IntEnum
from discord.opus import Encoder
from discord import FFmpegOpusAudio, VoiceClient

OPUS_DELAY = Encoder.FRAME_LENGTH / 1000.0


class MusicState(IntEnum):
    INTERRUPTED = 0
    STOPPED = 1
    CONTINUED = 2


def play(
    client: VoiceClient,
    source: FFmpegOpusAudio,
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
