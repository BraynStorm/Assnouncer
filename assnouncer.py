from asyncio.tasks import sleep
from asyncio.windows_events import SelectorEventLoop
from dataclasses import dataclass
import json
from logging import exception
from typing import List, NewType, Union, Type
from urllib import request
import discord
import os
from discord.gateway import DiscordClientWebSocketResponse
from discord.player import AudioPlayer
import pytube
import io
import regex
import traceback

from sclib import SoundcloudAPI
soundcloud = SoundcloudAPI()

client = discord.Client()


@dataclass
class G:
    mein_kampf: discord.Guild = None
    vc: discord.VoiceClient = None


gg = G()
queue = []


def levenshtein_ratio_and_distance(s, t):
    """levenshtein_ratio_and_distance:
    Calculates levenshtein distance between two strings.
    If ratio_calc = True, the function computes the
    levenshtein distance ratio of similarity between two strings
    For all i and j, distance[i,j] will contain the Levenshtein
    distance between the first i characters of s and the
    first j characters of t
    """
    import numpy as np

    # Initialize matrix of zeros
    rows = len(s) + 1
    cols = len(t) + 1
    distance = np.zeros((rows, cols), dtype=int)

    # Populate matrix of zeros with the indices of each character of both strings
    for i in range(1, rows):
        for k in range(1, cols):
            distance[i][0] = i
            distance[0][k] = k

    # Iterate over the matrix to compute the cost of deletions,insertions and/or substitutions
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row - 1] == t[col - 1]:
                cost = 0  # If the characters are the same in the two strings in a given position [i,j] then the cost is 0
            else:
                # In order to align the results with those of the Python Levenshtein package, if we choose to calculate the ratio
                # the cost of a substitution is 2. If we calculate just distance, then the cost of a substitution is 1.
                cost = 1
            distance[row][col] = min(
                distance[row - 1][col] + 1,  # Cost of deletions
                distance[row][col - 1] + 1,  # Cost of insertions
                distance[row - 1][col - 1] + cost,
            )  # Cost of substitutions
    return distance[row][col]


@client.event
async def on_ready():
    print("GETTING READY")
    await client.change_presence(activity=discord.Game(name="Getting ready"))

    gg.mein_kampf = client.get_guild(642747343208185857)
    gg.vc = await gg.mein_kampf.voice_channels[0].connect(timeout=2000, reconnect=True)

    await client.change_presence(activity=discord.Game(name="Ready"))
    print("READY")


def mostly_equal(a: str, b: str) -> bool:
    return levenshtein_ratio_and_distance(a, b) < 3

def is_link(link: str) -> bool:
    return link.startswith("http")

def is_soundcloud_link(link: str) -> bool:
    return link.startswith("https://www.soundcloud.com/") or link.startswith("https://soundcloud.com/")

def is_youtube_link(link: str) -> bool:
    return link.startswith("https://www.youtube.com/watch?v=") or link.startswith("https://youtube.com/watch?v=")


async def queue_song(q: str):
    if is_link(q):
        queue.append(q)
    elif len(q) > 3:
        if mostly_equal(q, "careless whisper"):
            q = "https://www.youtube.com/watch?v=iik25wqIuFo"
            queue.append(q)
        else:
            list_results: List[pytube.YouTube] = pytube.Search(q).fetch_and_parse()[0]
            queue.append(list_results[0].watch_url)
    else:
        return

    if len(queue) == 1:
        await play_queue()


async def send_to_general(msg):
    await gg.mein_kampf.text_channels[0].send(msg)

async def play_queue():
    while queue:
        if gg.vc.is_playing():
            await sleep(0.3)
            continue

        if not queue:
            continue

        print('after loopty loop')
        q: str = queue[0]

        if is_youtube_link(q):
            yt = pytube.YouTube(q)
            await send_to_general(f"Playing '{q}'")
            stream = yt.streams.get_audio_only()
            if stream:
                stream.download(filename="streamcache")
                src = await discord.FFmpegOpusAudio.from_probe(
                    source="streamcache",
                    executable=r"C:\Users\Braynstorm\Downloads\ffmpeg\ffmpeg.exe",
                )
                gg.vc.play(src, after=lambda x: queue.pop(0))
            else:
                await send_to_general(f"No audio-only stream found. Request will be skipped")
                if queue:
                    queue.pop()
        else:
            try:
                path = ""
                if is_soundcloud_link(q):
                    # NOTE(braynstorm): It's a soundcloud link
                    sc_stuff = soundcloud.resolve(q)
                    path = sc_stuff.get_stream_url();
                else:
                    # NOTE(braynstorm): It's a direct link. Download and play it
                    path, _ = request.urlretrieve(q, filename="downloads/tmp")

                src = await discord.FFmpegOpusAudio.from_probe(
                    source=path,
                    executable=r"C:\Users\Braynstorm\Downloads\ffmpeg\ffmpeg.exe",
                )
                gg.vc.play(src, after=lambda x: queue.pop(0))
            except:
                await send_to_general(traceback.format_exc())
                queue.pop(0)

@client.event
async def on_voice_state_update(
    member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
):
    if member != client.user:
        theme_path: str = f"theme_db/{member}"

        just_joined = before.channel is None and after.channel is not None
        just_unmuted = before.self_mute and not after.self_mute

        if just_joined:
            print("Joined!", str(member))
            if not os.path.exists(theme_path):
                print("No theme for", theme_path)
                return
            src = await discord.FFmpegOpusAudio.from_probe(
                source=theme_path,
                executable=r"C:\Users\Braynstorm\Downloads\ffmpeg\ffmpeg.exe",
            )
            if gg.vc.is_playing():
                old_source : AudioPlayer= gg.vc._player
                old_source.pause()

                gg.vc._player = None
                gg.vc.play(src)
                while gg.vc.is_playing():
                    await sleep(0.3)
                gg.vc.stop()

                gg.vc._player = old_source
                gg.vc.resume()
            else:
                gg.vc.play(src)


@client.event
async def on_message(msg: discord.Message):
    print(msg)

    theme_path: str = f"theme_db/{msg.author}"
    text_channel = gg.mein_kampf.text_channels[0]

    if not gg.vc:
        await on_ready()
        return
    elif msg.author == client.user:
        return
    elif msg.content == "queue":
        c: discord.TextChannel = msg.channel

        queue_str = "```Queue is empty```"
        if queue:
            queue_str = "```"
            for i, s in enumerate(queue):
                queue_str += f"{i}: {s}\n"
            queue_str += "\n```"
        await c.send(content=queue_str)
    elif msg.content == "stop" or msg.content == "не ме занимавай с твоите глупости" or msg.content == "dilyankata":
        queue.clear()
        gg.vc.stop()
    elif msg.content == "next":
        gg.vc.stop()
    elif msg.content.startswith("set my theme "):
        await text_channel.send("Setting your theme...")
        theme = msg.content[len("set my theme ") :]
        stream = pytube.YouTube(theme).streams.get_audio_only()
        if stream:
            stream.download(filename=theme_path)
            await text_channel.send("Done!")
        else:
            await text_channel.send("Failed to set your theme. Old one remains.")

    elif msg.content.startswith("move "):
        parts: List[str] = msg.content.split(" ")
        if len(parts) == 3:
            parts = list(map(int, parts[1:]))
            parts = min(parts), max(parts)

    elif msg.content.startswith("swap "):
        parts: List[str] = msg.content.split(" ")
        if len(parts) == 3:
            parts = list(map(int, parts[1:]))
            parts = min(parts), max(parts)

            first = queue[parts[0]]
            second = queue[parts[1]]
            queue[parts[0]] = second
            queue[parts[1]] = first

    elif msg.content.startswith("play "):
        q = msg.content[5:]
        await queue_song(q)


client.run(open('token').read())
