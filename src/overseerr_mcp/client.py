"""Wrappers around the Overseerr API with lightweight models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from . import overseerr


@dataclass
class PageInfo:
    pages: int


@dataclass
class Media:
    tmdbId: int | None
    status: int | None
    tvdbId: int | None = None


@dataclass
class Request:
    media: Media
    createdAt: str


@dataclass
class Page:
    results: Sequence[Request]
    pageInfo: PageInfo


@dataclass
class MovieDetails:
    title: str


@dataclass
class Season:
    seasonNumber: int


@dataclass
class Episode:
    episodeNumber: int
    name: str


@dataclass
class SeasonDetails:
    episodes: Sequence[Episode]


@dataclass
class TvDetails:
    name: str
    seasons: Sequence[Season]


class RequestsApi:
    """Wrapper for request listings."""

    def __init__(self, client: overseerr.Overseerr):
        self._client = client

    async def list(self, *, take: int, skip: int, filter: str | None = None) -> Page:
        params: dict[str, int | str] = {"take": take, "skip": skip}
        if filter:
            params["filter"] = filter

        data = await self._client.get_requests(params)

        results: list[Request] = []
        for item in data.get("results", []):
            media_data = item.get("media") or {}
            results.append(
                Request(
                    media=Media(
                        tmdbId=media_data.get("tmdbId"),
                        status=media_data.get("status"),
                        tvdbId=media_data.get("tvdbId"),
                    ),
                    createdAt=item.get("createdAt", ""),
                )
            )

        page_info = data.get("pageInfo") or {}
        return Page(results=results, pageInfo=PageInfo(pages=page_info.get("pages", 0)))


class MoviesApi:
    """Wrapper for movie specific endpoints."""

    def __init__(self, client: overseerr.Overseerr):
        self._client = client

    async def get(self, movie_id: int) -> MovieDetails:
        data = await self._client.get_movie_details(movie_id)
        return MovieDetails(title=data.get("title", ""))


class SeriesApi:
    """Wrapper for series specific endpoints."""

    def __init__(self, client: overseerr.Overseerr):
        self._client = client

    async def get(self, show_id: int) -> TvDetails:
        data = await self._client.get_tv_details(show_id)
        seasons = [
            Season(seasonNumber=season.get("seasonNumber", 0))
            for season in data.get("seasons", [])
        ]
        return TvDetails(name=data.get("name", ""), seasons=seasons)

    async def get_season(self, show_id: int, season_number: int) -> SeasonDetails:
        data = await self._client.get_season_details(show_id, season_number)
        episodes = [
            Episode(
                episodeNumber=episode.get("episodeNumber", 0),
                name=episode.get("name", f"Episode {episode.get('episodeNumber', 0)}"),
            )
            for episode in data.get("episodes", [])
        ]
        return SeasonDetails(episodes=episodes)


async def create_overseerr_apis(
    *, api_key: str, url: str, client: overseerr.Overseerr | None = None
) -> tuple[RequestsApi, MoviesApi, SeriesApi]:
    """Factory returning wrappers for the Overseerr API."""

    overseerr_client = client or overseerr.Overseerr(api_key=api_key, url=url)
    return (
        RequestsApi(overseerr_client),
        MoviesApi(overseerr_client),
        SeriesApi(overseerr_client),
    )

