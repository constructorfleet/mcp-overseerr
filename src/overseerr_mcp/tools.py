from collections.abc import Sequence
from datetime import datetime, timezone
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import json
import os
from pydantic import BaseModel
from . import overseerr
from .client import create_overseerr_apis
from .models import MediaRequestsFilter, MediaStatus, StatusToolInput, TvRequestsFilter

# Constants for tool names
TOOL_GET_STATUS = "overseerr_status"
TOOL_GET_MOVIE_REQUESTS = "overseerr_movie_requests"
TOOL_GET_TV_REQUESTS = "overseerr_tv_requests"

# Environment variables
api_key = os.getenv("OVERSEERR_API_KEY", "")
url = os.getenv("OVERSEERR_URL", "")

if not api_key or not url:
    raise ValueError("OVERSEERR_API_KEY and OVERSEERR_URL environment variables are required")

# Media status mapping
MEDIA_STATUS_MAPPING = {
    1: "UNKNOWN",
    2: "PENDING", 
    3: "PROCESSING",
    4: "PARTIALLY_AVAILABLE",
    5: "AVAILABLE"
}

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
    ):
        self.name = tool_name
        self.input_model = input_model
        self._description = description
        self._tags = tuple(tags or ())

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
    def __init__(self):
        super().__init__(
            TOOL_GET_STATUS,
            StatusToolInput,
            description="Check the current Overseerr server health and report status details.",
            tags=("overseerr", "status"),
        )

    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        # Create asynchronous client
        client = overseerr.Overseerr(api_key=api_key, url=url)
        data = await client.get_status()

        if "version" in data:
            status_response = f"\n---\nOverseerr is available and these are the status data:\n"
            status_response += "\n- " + "\n- ".join([f"{key}: {val}" for key, val in data.items()])
        else:
            status_response = f"\n---\nOverseerr is not available and below is the request error: \n"
            status_response += "\n- " + "\n- ".join([f"{key}: {val}" for key, val in data.items()])

        return [
            TextContent(
                type="text",
                text=status_response
            )
        ]

class MovieRequestsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(
            TOOL_GET_MOVIE_REQUESTS,
            MediaRequestsFilter,
            description="List Overseerr movie requests filtered by optional status and start date.",
            tags=("overseerr", "movie", "requests"),
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
        requests_api, movies_api, _ = await create_overseerr_apis(api_key=api_key, url=url)

        normalized_start_date = _normalize_to_utc(start_date)

        take = 20
        skip = 0
        has_more = True
        status_filter = getattr(status, "value", status) if status else None

        results: list[dict[str, object]] = []

        while has_more:
            page = await requests_api.list(take=take, skip=skip, filter=status_filter)

            for result in page.results:
                media_info = result.media
                if not media_info or media_info.tvdbId:
                    continue

                created_at = result.createdAt
                created_at_dt = _normalize_to_utc(_parse_datetime(created_at))
                if (
                    normalized_start_date
                    and created_at_dt
                    and normalized_start_date > created_at_dt
                ):
                    continue

                movie_id = media_info.tmdbId
                if movie_id is None:
                    continue

                movie_details = await movies_api.get(movie_id)

                media_status_code = media_info.status or 1
                media_availability = MEDIA_STATUS_MAPPING.get(
                    media_status_code, "UNKNOWN"
                )

                results.append(
                    {
                        "title": movie_details.title or "Unknown Movie",
                        "media_availability": media_availability,
                        "request_date": created_at,
                    }
                )

            total_pages = getattr(page.pageInfo, "pages", 0)
            if total_pages <= (skip // take) + 1:
                has_more = False
            else:
                skip += take

        return results

class TvRequestsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(
            TOOL_GET_TV_REQUESTS,
            TvRequestsFilter,
            description="List Overseerr TV requests filtered by optional status and start date.",
            tags=("overseerr", "tv", "requests"),
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
        requests_api, _, series_api = await create_overseerr_apis(
            api_key=api_key, url=url
        )

        normalized_start_date = _normalize_to_utc(start_date)

        take = 20
        skip = 0
        has_more = True
        status_filter = getattr(status, "value", status) if status else None

        results: list[dict[str, object]] = []

        while has_more:
            page = await requests_api.list(take=take, skip=skip, filter=status_filter)

            for result in page.results:
                media_info = result.media
                if not media_info or not media_info.tvdbId:
                    continue

                created_at = result.createdAt
                created_at_dt = _normalize_to_utc(_parse_datetime(created_at))
                if (
                    normalized_start_date
                    and created_at_dt
                    and normalized_start_date > created_at_dt
                ):
                    continue

                tv_id = media_info.tmdbId
                if tv_id is None:
                    continue

                tv_details = await series_api.get(tv_id)

                media_status_code = media_info.status or 1
                tv_title_availability = MEDIA_STATUS_MAPPING.get(
                    media_status_code, "UNKNOWN"
                )

                for season in tv_details.seasons:
                    season_number = season.seasonNumber
                    if season_number == 0:
                        continue

                    season_details = await series_api.get_season(tv_id, season_number)

                    episode_details = []
                    for episode in season_details.episodes:
                        episode_number = episode.episodeNumber
                        episode_details.append(
                            {
                                "episode_number": f"{episode_number:02d}",
                                "episode_name": episode.name,
                            }
                        )

                    results.append(
                        {
                            "tv_title": tv_details.name or "Unknown TV Show",
                            "tv_title_availability": tv_title_availability,
                            "tv_season": f"S{season_number:02d}",
                            "tv_season_availability": tv_title_availability,
                            "tv_episodes": episode_details,
                            "request_date": created_at,
                        }
                    )

            total_pages = getattr(page.pageInfo, "pages", 0)
            if total_pages <= (skip // take) + 1:
                has_more = False
            else:
                skip += take

        return results
