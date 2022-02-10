from __future__ import annotations
import asyncio

import time

from dataclasses import dataclass
from typing import Callable
from discord.opus import Encoder
from discord import FFmpegOpusAudio, VoiceClient

OPUS_DELAY = Encoder.FRAME_LENGTH / 1000.0


@dataclass
class AudioPlayer:
    client: VoiceClient
    source: FFmpegOpusAudio = None

    def run(self, callback: Callable[[], bool] = None):
        if not self.client._connected.is_set():
            raise ValueError("Not connected to voice.")

        if not self.client.encoder and not self.source.is_opus():
            self.client.encoder = Encoder()

        loops = 0
        time_now = time.perf_counter()

        while True:
            if not self.client._connected.is_set():
                self.client._connected.wait()

                loops = 0
                time_now = time.perf_counter()

            data = self.source.read()
            if not data:
                break

            loops += 1

            self.send(data, encode=not self.source.is_opus())

            if callback is not None and callback():
                if self.source is None:
                    break

                loops = 0
                time_now = time.perf_counter()

                continue

            time_next = time_now + OPUS_DELAY * loops
            delay = max(0, OPUS_DELAY + (time_next - time.perf_counter()))

            time.sleep(delay)

    def send(self, data: bytes, encode: bool = True):
        self.client.send_audio_packet(data, encode=encode)

    def set_speaking(self, speaking):
        asyncio.run_coroutine_threadsafe(
            self.client.ws.speak(speaking), self.client.loop)
