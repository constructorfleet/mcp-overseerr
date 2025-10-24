from collections.abc import Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import os
from typing import Any, AsyncIterator

from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from pydantic import BaseModel

from .client import OverseerrApis
from .models import MediaRequestsFilter, MediaStatus, StatusToolInput, TvRequestsFilter

OverseerrFactory = Callable[[], OverseerrApis]

# Constants for tool names
TOOL_GET_STATUS = "overseerr_status"
TOOL_GET_MOVIE_REQUESTS = "overseerr_movie_requests"
TOOL_GET_TV_REQUESTS = "overseerr_tv_requests"

# Environment variables
def _load_overseerr_environment() -> tuple[str, str]:
    api_key = os.getenv("OVERSEERR_API_KEY", "")
    url = os.getenv("OVERSEERR_URL", "")

    if not api_key or not url:
        raise ValueError(
            "OVERSEERR_API_KEY and OVERSEERR_URL environment variables are required"
        )

    return url, api_key


_OVERSEERR_URL, _OVERSEERR_API_KEY = _load_overseerr_environment()


def create_overseerr_apis() -> OverseerrApis:
    return OverseerrApis(base_url=_OVERSEERR_URL, api_key=_OVERSEERR_API_KEY)

# Media status mapping
MEDIA_STATUS_MAPPING = {
    1: "UNKNOWN",
    2: "PENDING",
    3: "PROCESSING",
    4: "PARTIALLY_AVAILABLE",
    5: "AVAILABLE"
}

REQUEST_PAGE_SIZE = 20


def _to_plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, tuple):
        return [_to_plain(v) for v in value]
    if isinstance(value, set):
        return [_to_plain(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "to_dict"):
        return _to_plain(value.to_dict())
    if is_dataclass(value):
        return _to_plain(asdict(value))
    if hasattr(value, "__dict__"):
        return _to_plain({k: getattr(value, k) for k in vars(value)})
    return value


@asynccontextmanager
async def _overseerr_client(
    overseerr_factory: OverseerrFactory,
) -> AsyncIterator[OverseerrApis]:
    client = overseerr_factory()
    try:
        yield client
    finally:
        await client.aclose()


async def _iter_request_pages(
    client: OverseerrApis,
    *,
    status_filter: str | None,
    take: int = REQUEST_PAGE_SIZE,
) -> AsyncIterator[dict[str, Any]]:
    skip = 0
    while True:
        response = await client.get_requests(take=take, skip=skip, filter=status_filter)
        page = _to_plain(response)
        yield page

        page_info = _to_plain(page.get("pageInfo") or page.get("page_info") or {})
        total_pages = int(page_info.get("pages") or 0)
        current_page = (skip // take) + 1
        if total_pages <= current_page or total_pages == 0:
            break

        skip += take

def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None

    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _normalize_to_utc(dt: datetime | None) -> datetime | None:
    if not dt:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


class ToolHandler():
    def __init__(
        self,
        tool_name: str,
        input_model: type[BaseModel] | None = None,
        *,
        description: str,
        tags: Sequence[str] | None = None,
        overseerr_factory: OverseerrFactory = create_overseerr_apis,
    ):
        self.name = tool_name
        self.input_model = input_model
        self._description = description
        self._tags = tuple(tags or ())
        self._overseerr_factory = overseerr_factory

    def _get_input_schema(self) -> dict:
        if not self.input_model:
            return {"type": "object", "properties": {}}
        return self.input_model.model_json_schema()

    def _validate_args(self, args: dict) -> dict:
        if not self.input_model:
            return {}
        return self.input_model.model_validate(args).model_dump()

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            description=self._description,
            inputSchema=self._get_input_schema(),
            tags=list(self._tags),
        )

    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError()

class StatusToolHandler(ToolHandler):
    def __init__(
        self,
        *,
        overseerr_factory: OverseerrFactory = create_overseerr_apis,
    ):
        super().__init__(
            TOOL_GET_STATUS,
            StatusToolInput,
            description="Check the current Overseerr server health and report status details.",
            tags=("overseerr", "status"),
            overseerr_factory=overseerr_factory,
        )

    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        async with _overseerr_client(self._overseerr_factory) as client:
            data = _to_plain(await client.get_status())

        if isinstance(data, dict) and "version" in data:
            status_response = "\n---\nOverseerr is available and these are the status data:\n"
            status_response += "\n- " + "\n- ".join([f"{key}: {val}" for key, val in data.items()])
        else:
            status_response = "\n---\nOverseerr is not available and below is the request error: \n"
            if isinstance(data, dict):
                status_response += "\n- " + "\n- ".join(
                    [f"{key}: {val}" for key, val in data.items()]
                )
            else:
                status_response += f"\n- {data}"

        return [
            TextContent(
                type="text",
                text=status_response
            )
        ]

class MovieRequestsToolHandler(ToolHandler):
    def __init__(
        self,
        *,
        overseerr_factory: OverseerrFactory = create_overseerr_apis,
    ):
        super().__init__(
            TOOL_GET_MOVIE_REQUESTS,
            MediaRequestsFilter,
            description="List Overseerr movie requests filtered by optional status and start date.",
            tags=("overseerr", "movie", "requests"),
            overseerr_factory=overseerr_factory,
        )

    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        filters = self._validate_args(args)

        # Now using asynchronous approach
        results = await self.get_movie_requests(**filters)
        
        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]
        
    async def get_movie_requests(
        self,
        status: MediaStatus | None = None,
        start_date: datetime | None = None,
    ):
        normalized_start_date = _normalize_to_utc(start_date)

        status_filter = getattr(status, "value", status) if status else None

        results: list[dict[str, object]] = []
        async with _overseerr_client(self._overseerr_factory) as client:
            async for page in _iter_request_pages(client, status_filter=status_filter):
                for result in page.get("results", []):
                    result_data = _to_plain(result)
                    media_info = _to_plain(result_data.get("media"))

                    if not media_info or media_info.get("tvdbId"):
                        continue

                    created_at = result_data.get("createdAt") or result_data.get("created_at")
                    created_at_dt = _normalize_to_utc(_parse_datetime(created_at or ""))
                    if (
                        normalized_start_date
                        and created_at_dt
                        and normalized_start_date > created_at_dt
                    ):
                        continue

                    movie_id = media_info.get("tmdbId") or media_info.get("tmdb_id")
                    if movie_id is None:
                        continue

                    movie_details = _to_plain(
                        await client.get_movie_by_movie_id(int(movie_id))
                    )

                    media_status_code = media_info.get("status") or 1
                    media_availability = MEDIA_STATUS_MAPPING.get(
                        int(media_status_code), "UNKNOWN"
                    )

                    results.append(
                        {
                            "title": movie_details.get("title")
                            or movie_details.get("name")
                            or "Unknown Movie",
                            "media_availability": media_availability,
                            "request_date": created_at,
                        }
                    )

        return results

class TvRequestsToolHandler(ToolHandler):
    def __init__(
        self,
        *,
        overseerr_factory: Callable[[], OverseerrApis] = create_overseerr_apis,
    ):
        super().__init__(
            TOOL_GET_TV_REQUESTS,
            TvRequestsFilter,
            description="List Overseerr TV requests filtered by optional status and start date.",
            tags=("overseerr", "tv", "requests"),
            overseerr_factory=overseerr_factory,
        )

    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        filters = self._validate_args(args)

        # Now using asynchronous approach
        results = await self.get_tv_requests(**filters)
        
        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]
        
    async def get_tv_requests(
        self,
        status: MediaStatus | None = None,
        start_date: datetime | None = None,
    ):
        normalized_start_date = _normalize_to_utc(start_date)

        status_filter = getattr(status, "value", status) if status else None

        results: list[dict[str, object]] = []
        async with _overseerr_client(self._overseerr_factory) as client:
            async for page in _iter_request_pages(client, status_filter=status_filter):
                for result in page.get("results", []):
                    result_data = _to_plain(result)
                    media_info = _to_plain(result_data.get("media"))
                    if not media_info or not media_info.get("tvdbId"):
                        continue

                    created_at = result_data.get("createdAt") or result_data.get("created_at")
                    created_at_dt = _normalize_to_utc(_parse_datetime(created_at or ""))
                    if (
                        normalized_start_date
                        and created_at_dt
                        and normalized_start_date > created_at_dt
                    ):
                        continue

                    tv_id = media_info.get("tmdbId") or media_info.get("tmdb_id")
                    if tv_id is None:
                        continue

                    tv_details = _to_plain(await client.get_tv_by_tv_id(int(tv_id)))

                    media_status_code = media_info.get("status") or 1
                    tv_title_availability = MEDIA_STATUS_MAPPING.get(
                        int(media_status_code), "UNKNOWN"
                    )

                    for season in tv_details.get("seasons", []):
                        season_data = _to_plain(season)
                        season_number = season_data.get("seasonNumber") or season_data.get(
                            "season_number"
                        )
                        if not season_number or int(season_number) == 0:
                            continue

                        season_details = _to_plain(
                            await client.get_tv_season_by_season_id(
                                int(tv_id), int(season_number)
                            )
                        )

                        episode_details = []
                        for episode in season_details.get("episodes", []):
                            episode_data = _to_plain(episode)
                            episode_number = (
                                episode_data.get("episodeNumber")
                                or episode_data.get("episode_number")
                                or 0
                            )
                            name = (
                                episode_data.get("name")
                                or episode_data.get("title")
                                or f"Episode {episode_number}"
                            )
                            episode_details.append(
                                {
                                    "episode_number": f"{int(episode_number):02d}",
                                    "episode_name": name,
                                }
                            )

                        results.append(
                            {
                                "tv_title": tv_details.get("name")
                                or tv_details.get("title")
                                or "Unknown TV Show",
                                "tv_title_availability": tv_title_availability,
                                "tv_season": f"S{int(season_number):02d}",
                                "tv_season_availability": tv_title_availability,
                                "tv_episodes": episode_details,
                                "request_date": created_at,
                            }
                        )

        return results
