from collections.abc import Sequence
from datetime import datetime
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


class ToolHandler():
    def __init__(self, tool_name: str, input_model: type[BaseModel] | None = None):
        self.name = tool_name
        self.input_model = input_model

    def _get_input_schema(self) -> dict:
        if not self.input_model:
            return {"type": "object", "properties": {}}
        return self.input_model.model_json_schema()

    def _validate_args(self, args: dict) -> dict:
        if not self.input_model:
            return {}
        return self.input_model.model_validate(args).model_dump()

    def get_tool_description(self) -> Tool:
        raise NotImplementedError()

    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError()

class StatusToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_GET_STATUS, StatusToolInput)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get the status of the Overseerr server.",
            inputSchema=self._get_input_schema(),
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
        super().__init__(TOOL_GET_MOVIE_REQUESTS, MediaRequestsFilter)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get the list of all movie requests that satisfies the filter arguments.",
            inputSchema=self._get_input_schema(),
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
        client = overseerr.Overseerr(api_key=api_key, url=url)

        # Initialize pagination parameters
        take = 20  # Number of items per page
        skip = 0   # Starting offset
        has_more = True

        all_results = []
        
        # Process all pages
        while has_more:
            # Prepare params
            params = {
                "take": take,
                "skip": skip
            }
            
            # Add filter if specified
            if status:
                status_value = getattr(status, "value", status)
                params["filter"] = status_value

            # Call API
            response = await client.get_requests(params)
            
            # Process results
            results = response.get("results", [])
            
            for result in results:
                # Only process if it's a movie (no tvdbId)
                media_info = result.get("media", {})
                if media_info and not media_info.get("tvdbId"):
                    # Check if request date matches the filter if provided
                    created_at = result.get("createdAt", "")
                    created_at_dt = _parse_datetime(created_at)
                    if start_date and created_at_dt and start_date > created_at_dt:
                        continue
                    
                    # Get movie details to get the title
                    movie_id = media_info.get("tmdbId")
                    movie_details = await client.get_movie_details(movie_id)
                    
                    # Map media availability to string value
                    media_status_code = media_info.get("status", 1)
                    media_availability = MEDIA_STATUS_MAPPING.get(media_status_code, "UNKNOWN")
                    
                    # Create formatted result
                    formatted_result = {
                        "title": movie_details.get("title", "Unknown Movie"),
                        "media_availability": media_availability,
                        "request_date": created_at
                    }
                    
                    all_results.append(formatted_result)
            
            # Check if there are more pages
            page_info = response.get("pageInfo", {})
            if page_info.get("pages", 0) <= (skip // take) + 1:
                has_more = False
            else:
                skip += take
        
        return all_results

class TvRequestsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_GET_TV_REQUESTS, TvRequestsFilter)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get the list of all TV requests that satisfies the filter arguments.",
            inputSchema=self._get_input_schema(),
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
        client = overseerr.Overseerr(api_key=api_key, url=url)

        # Initialize pagination parameters
        take = 20  # Number of items per page
        skip = 0   # Starting offset
        has_more = True
        
        all_results = []
        
        # Process all pages
        while has_more:
            # Prepare params
            params = {
                "take": take,
                "skip": skip
            }
            
            # Add filter if specified
            if status:
                status_value = getattr(status, "value", status)
                params["filter"] = status_value
            
            # Call API
            response = await client.get_requests(params)
            
            # Process results
            results = response.get("results", [])
            
            for result in results:
                # Only process if it's a TV show (has tvdbId)
                media_info = result.get("media", {})
                if media_info and media_info.get("tvdbId"):
                    # Check if request date matches the filter if provided
                    created_at = result.get("createdAt", "")
                    created_at_dt = _parse_datetime(created_at)
                    if start_date and created_at_dt and start_date > created_at_dt:
                        continue
                    
                    # Get TV details to get the title and seasons
                    tv_id = media_info.get("tmdbId")
                    tv_details = await client.get_tv_details(tv_id)
                    
                    # Map media availability to string value
                    media_status_code = media_info.get("status", 1)
                    tv_title_availability = MEDIA_STATUS_MAPPING.get(media_status_code, "UNKNOWN")
                    
                    # Get seasons information
                    seasons = tv_details.get("seasons", [])
                    
                    # For each season, get more detailed info including episodes
                    for season in seasons:
                        season_number = season.get("seasonNumber", 0)
                        
                        # Skip if it's a special season (season 0)
                        if season_number == 0:
                            continue
                        
                        # Format season string (e.g., S01)
                        season_str = f"S{season_number:02d}"
                        
                        # Get detailed season info including episodes
                        season_details = await client.get_season_details(tv_id, season_number)
                        
                        # Season availability is assumed to be the same as the show
                        tv_season_availability = tv_title_availability
                        
                        # Process episodes
                        episodes = season_details.get("episodes", [])
                        episode_details = []
                        
                        for episode in episodes:
                            episode_number = episode.get("episodeNumber", 0)
                            episode_details.append({
                                "episode_number": f"{episode_number:02d}",
                                "episode_name": episode.get("name", f"Episode {episode_number}")
                            })
                        
                        # Create formatted result for this season
                        formatted_result = {
                            "tv_title": tv_details.get("name", "Unknown TV Show"),
                            "tv_title_availability": tv_title_availability,
                            "tv_season": season_str,
                            "tv_season_availability": tv_season_availability,
                            "tv_episodes": episode_details,
                            "request_date": created_at
                        }

                        all_results.append(formatted_result)

            # Check if there are more pages
            page_info = response.get("pageInfo", {})
            if page_info.get("pages", 0) <= (skip // take) + 1:
                has_more = False
            else:
                skip += take

        return all_results
