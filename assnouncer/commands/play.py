from __future__ import annotations

import logging

from assnouncer import util
from assnouncer.asspp import String, Timestamp
from assnouncer.commands.base import BaseCommand

from dataclasses import dataclass
from typing import List, ClassVar
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Play(BaseCommand):
    ALIASES: ClassVar[List[str]] = ["play", "Play", "плаъ", "πλαυ", "playing"]

    async def spotify_playlist(self, payload: String) -> bool:
        # Playing a spotify playlist is tricky.
        # We need to extract the playlist's content - track name and artist name.
        # Then queue all the tracks in the playlist individually and in order.
        #
        # We can use the Spotify API to get the playlist's content.

        # Spotify Playlist URL:
        # https://open.spotify.com/playlist/0ujGnKjMRi7yCGsLmUn8fa?si=90185d6fac534bb9

        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        # Extract the playlist ID from the URL
        playlist_id = payload.value.split("/")[-1].split("?")[0]

        # Spotify API credentials
        # https://developer.spotify.com/dashboard/5a69cbdf411543edaf555ceae205e433/settings
        client_id = "5a69cbdf411543edaf555ceae205e433"
        client_secret = Path("spotify_token").read_text().strip()

        # Spotify API client
        client_credentials_manager = SpotifyClientCredentials(
            client_id=client_id, client_secret=client_secret
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

        # Get the playlist's content
        playlist = sp.playlist(
            playlist_id, fields="tracks.items(track(name, artists(name)))"
        )
        for track in playlist["tracks"]["items"]:
            track_name = track["track"]["name"]
            artist_name = track["track"]["artists"][0]["name"]
            query = f"{artist_name} - {track_name}"
            uri = await util.resolve_uri(query)
            if uri is None:
                logger.warn(f"No source found for '{query}'")
                await self.respond(f"No source found for '{query}' - skipping song")
            else:
                requested_by_user = self.message.author
                requested_by = (
                    f"{requested_by_user.name}#{requested_by_user.discriminator}"
                )
                request = util.download(
                    query,
                    uri,
                    start=None,
                    stop=None,
                    channel=self.channel,
                    user=requested_by,
                )
                await self.ass.queue_song(request)
        return True

    async def on_command(self, payload: String, start: Timestamp = None, stop: Timestamp = None):
        """
        Add a song to Assnouncer's queue.

        :param payload: Url or Youtube query for the song.
        :param start: (Optional) Start timestamp within the song.
        :param stop: (Optional) End timestamp within the song.
        """

        # Spotify Playlist URL handling.
        spotify_playlist = "https://open.spotify.com/playlist/"
        if payload.value.startswith(spotify_playlist):
            await self.spotify_playlist(payload)
            return

        uri = await util.resolve_uri(payload.value)
        if uri is None:
            logger.warn(f"No source found for '{payload.value}'")
            await self.respond("No source found - skipping song")
        else:
            requested_by_user = self.message.author
            requested_by = f"{requested_by_user.name}#{requested_by_user.discriminator}"
            request = util.download(
                payload.value,
                uri,
                start=start,
                stop=stop,
                channel=self.channel,
                user=requested_by,
            )
            await self.ass.queue_song(request)
