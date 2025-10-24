"""Async wrappers around the official Overseerr Python SDK."""

from __future__ import annotations

import asyncio
from typing import Any

import overseerr


class OverseerrApis:
    """Facade exposing async accessors backed by the Overseerr SDK."""

    def __init__(self, *, base_url: str, api_key: str) -> None:
        self._config = overseerr.Configuration()
        sanitized_url = base_url.rstrip("/")
        self._config.host = f"{sanitized_url}/api/v1"
        self._config.api_key["apiKey"] = api_key

        self._client = overseerr.ApiClient(self._config)
        self._public_api = overseerr.PublicApi(self._client)
        self._request_api = overseerr.RequestApi(self._client)
        self._movies_api = overseerr.MoviesApi(self._client)
        self._tv_api = overseerr.TvApi(self._client)

    async def get_status(self) -> Any:
        return await asyncio.to_thread(self._public_api.get_status)

    async def get_requests(
        self, *, take: int, skip: int, filter: str | None = None
    ) -> Any:
        return await asyncio.to_thread(
            self._request_api.get_request, take=take, skip=skip, filter=filter
        )

    async def get_movie_by_movie_id(self, movie_id: int) -> Any:
        return await asyncio.to_thread(
            self._movies_api.get_movie_by_movie_id, movie_id
        )

    async def get_tv_by_tv_id(self, tv_id: int) -> Any:
        return await asyncio.to_thread(self._tv_api.get_tv_by_tv_id, tv_id)

    async def get_tv_season_by_season_id(self, tv_id: int, season_id: int) -> Any:
        return await asyncio.to_thread(
            self._tv_api.get_tv_season_by_season_id, tv_id, season_id
        )

    async def aclose(self) -> None:
        await asyncio.to_thread(self._client.close)
