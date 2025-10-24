import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("OVERSEERR_API_KEY", "test")
os.environ.setdefault("OVERSEERR_URL", "http://localhost")

import pytest

from overseerr_mcp.models import MediaRequestsFilter, MediaStatus, TvRequestsFilter
from overseerr_mcp.tools import (
    MovieRequestsToolHandler,
    StatusToolHandler,
    TvRequestsToolHandler,
)


@dataclass
class FakePageInfo:
    pages: int


@dataclass
class FakeMedia:
    tmdbId: int
    status: int
    tvdbId: int | None = None


@dataclass
class FakeMovieRequest:
    media: FakeMedia
    createdAt: str


@dataclass
class FakeTvRequest:
    media: FakeMedia
    createdAt: str


@dataclass
class FakePage:
    results: Sequence[Any]
    pageInfo: FakePageInfo


@dataclass
class FakeMovieDetails:
    title: str


@dataclass
class FakeSeason:
    seasonNumber: int


@dataclass
class FakeEpisode:
    episodeNumber: int
    name: str


@dataclass
class FakeSeasonDetails:
    episodes: Sequence[FakeEpisode]


@dataclass
class FakeTvDetails:
    name: str
    seasons: Sequence[FakeSeason]



def test_movie_handler_validates_arguments_with_input_model(monkeypatch):
    handler = MovieRequestsToolHandler()

    captured = {}

    async def fake_get_movie_requests(*args, **kwargs):
        if args:
            captured["positional"] = args
            return []

        captured["status"] = kwargs.get("status")
        captured["start_date"] = kwargs.get("start_date")
        return []

    monkeypatch.setattr(handler, "get_movie_requests", fake_get_movie_requests)

    args = {
        "status": "available",
        "start_date": "2020-09-12T10:00:27Z",
    }

    async def invoke():
        return await handler.run_tool(args)

    response = asyncio.run(invoke())

    assert "positional" not in captured
    assert captured["status"] == MediaStatus.available
    assert captured["start_date"] == datetime(2020, 9, 12, 10, 0, 27, tzinfo=timezone.utc)
    assert json.loads(response[0].text) == []
    assert handler.input_model is MediaRequestsFilter


def test_movie_request_filters_use_typed_values(monkeypatch):
    handler = MovieRequestsToolHandler()

    class FakeClient:
        def __init__(self):
            self.request_params = []
            self.request_calls = 0

        async def get_requests(self, params):
            self.request_params.append(params)
            self.request_calls += 1
            return {
                "results": [
                    {
                        "media": {"tmdbId": 1, "status": 2},
                        "createdAt": "2020-09-13T10:00:27.000Z",
                    },
                    {
                        "media": {"tmdbId": 2, "status": 5},
                        "createdAt": "2020-09-11T10:00:27.000Z",
                    },
                ],
                "pageInfo": {"pages": 1},
            }

        async def get_movie_details(self, movie_id):
            return {"title": f"movie-{movie_id}"}

    fake_client = FakeClient()

    async def fake_constructor(*args, **kwargs):
        return fake_client

    monkeypatch.setattr("overseerr_mcp.tools.overseerr.Overseerr", lambda **kwargs: fake_client)

    results = asyncio.run(
        handler.get_movie_requests(
            status=MediaStatus.pending,
            start_date=datetime(2020, 9, 12, 10, 0, 27, tzinfo=timezone.utc),
        )
    )

    assert fake_client.request_params[0]["filter"] == "pending"
    assert results == [
        {
            "title": "movie-1",
            "media_availability": "PENDING",
            "request_date": "2020-09-13T10:00:27.000Z",
        }
    ]


def test_tv_handler_validates_arguments_with_input_model(monkeypatch):
    handler = TvRequestsToolHandler()

    captured = {}

    async def fake_get_tv_requests(*args, **kwargs):
        if args:
            captured["positional"] = args
            return []

        captured["status"] = kwargs.get("status")
        captured["start_date"] = kwargs.get("start_date")
        return []

    monkeypatch.setattr(handler, "get_tv_requests", fake_get_tv_requests)

    args = {
        "status": "approved",
        "start_date": "2020-09-12T10:00:27Z",
    }

    response = asyncio.run(handler.run_tool(args))

    assert "positional" not in captured
    assert captured["status"] == MediaStatus.approved
    assert captured["start_date"] == datetime(2020, 9, 12, 10, 0, 27, tzinfo=timezone.utc)
    assert json.loads(response[0].text) == []
    assert handler.input_model is TvRequestsFilter


def test_tool_descriptions_include_expected_tags():
    tool_tags = {
        MovieRequestsToolHandler: {"overseerr", "movie", "requests"},
        TvRequestsToolHandler: {"overseerr", "tv", "requests"},
        StatusToolHandler: {"overseerr", "status"},
    }

    for handler_cls, expected_tags in tool_tags.items():
        handler = handler_cls()
        tool_description = handler.get_tool_description()

        assert hasattr(tool_description, "tags"), handler_cls.__name__
        assert set(tool_description.tags) == expected_tags


def test_tool_descriptions_and_arguments_are_documented():
    expectations = {
        MovieRequestsToolHandler: {
            "description": "List Overseerr movie requests filtered by optional status and start date.",
            "arguments": {
                "status": (
                    "Limit results to requests matching the Overseerr status (approved, available, "
                    "pending, processing, unavailable, failed)."
                ),
                "start_date": (
                    "Return requests created on or after the provided ISO 8601 timestamp "
                    "(e.g. 2020-09-12T10:00:27Z)."
                ),
            },
        },
        TvRequestsToolHandler: {
            "description": "List Overseerr TV requests filtered by optional status and start date.",
            "arguments": {
                "status": (
                    "Limit results to requests matching the Overseerr status (approved, available, "
                    "pending, processing, unavailable, failed)."
                ),
                "start_date": (
                    "Return requests created on or after the provided ISO 8601 timestamp "
                    "(e.g. 2020-09-12T10:00:27Z)."
                ),
            },
        },
        StatusToolHandler: {
            "description": "Check the current Overseerr server health and report status details.",
            "arguments": {},
        },
    }

    for handler_cls, expectation in expectations.items():
        handler = handler_cls()
        tool_description = handler.get_tool_description()

        assert tool_description.description == expectation["description"], handler_cls.__name__

        input_schema = tool_description.inputSchema or {}
        properties = input_schema.get("properties", {})

        assert set(properties.keys()) >= set(expectation["arguments"].keys())

        for argument, description in expectation["arguments"].items():
            assert properties[argument]["description"] == description


class FakeRequestsApi:
    def __init__(self, pages: list[FakePage]):
        self._pages = pages
        self.calls: list[dict[str, Any]] = []

    async def list(self, *, take: int, skip: int, filter: str | None = None) -> FakePage:
        self.calls.append({"take": take, "skip": skip, "filter": filter})
        return self._pages.pop(0)


class FakeMoviesApi:
    def __init__(self, responses: dict[int, FakeMovieDetails]):
        self._responses = responses
        self.calls: list[int] = []

    async def get(self, movie_id: int) -> FakeMovieDetails:
        self.calls.append(movie_id)
        return self._responses[movie_id]


class FakeSeriesApi:
    def __init__(self, shows: dict[int, FakeTvDetails], seasons: dict[tuple[int, int], FakeSeasonDetails]):
        self._shows = shows
        self._seasons = seasons
        self.detail_calls: list[int] = []
        self.season_calls: list[tuple[int, int]] = []

    async def get(self, show_id: int) -> FakeTvDetails:
        self.detail_calls.append(show_id)
        return self._shows[show_id]

    async def get_season(self, show_id: int, season_number: int) -> FakeSeasonDetails:
        self.season_calls.append((show_id, season_number))
        return self._seasons[(show_id, season_number)]


@pytest.mark.asyncio
async def test_movie_requests_handler_uses_sdk_factory(monkeypatch):
    handler = MovieRequestsToolHandler()

    requests_api = FakeRequestsApi(
        [
            FakePage(
                results=[
                    FakeMovieRequest(
                        media=FakeMedia(tmdbId=101, status=5),
                        createdAt="2020-09-13T10:00:27.000Z",
                    )
                ],
                pageInfo=FakePageInfo(pages=1),
            )
        ]
    )
    movies_api = FakeMoviesApi({101: FakeMovieDetails(title="Movie 101")})
    series_api = FakeSeriesApi({}, {})

    async def fake_factory(*args, **kwargs):
        return requests_api, movies_api, series_api

    monkeypatch.setattr("overseerr_mcp.tools.create_overseerr_apis", fake_factory)

    results = await handler.get_movie_requests(status=MediaStatus.available)

    assert requests_api.calls == [
        {"take": 20, "skip": 0, "filter": MediaStatus.available.value}
    ]
    assert movies_api.calls == [101]
    assert results == [
        {
            "title": "Movie 101",
            "media_availability": "AVAILABLE",
            "request_date": "2020-09-13T10:00:27.000Z",
        }
    ]


@pytest.mark.asyncio
async def test_tv_requests_handler_fetches_season_details(monkeypatch):
    handler = TvRequestsToolHandler()

    tv_request = FakeTvRequest(
        media=FakeMedia(tmdbId=202, status=3, tvdbId=555),
        createdAt="2020-09-14T10:00:27.000Z",
    )
    requests_api = FakeRequestsApi(
        [
            FakePage(
                results=[tv_request],
                pageInfo=FakePageInfo(pages=1),
            )
        ]
    )

    show_details = FakeTvDetails(
        name="Show 202",
        seasons=[FakeSeason(seasonNumber=0), FakeSeason(seasonNumber=1)],
    )
    season_details = FakeSeasonDetails(
        episodes=[FakeEpisode(episodeNumber=1, name="Pilot")]
    )

    series_api = FakeSeriesApi(
        shows={202: show_details},
        seasons={(202, 1): season_details},
    )
    movies_api = FakeMoviesApi({})

    async def fake_factory(*args, **kwargs):
        return requests_api, movies_api, series_api

    monkeypatch.setattr("overseerr_mcp.tools.create_overseerr_apis", fake_factory)

    results = await handler.get_tv_requests(status=MediaStatus.processing)

    assert requests_api.calls == [
        {"take": 20, "skip": 0, "filter": MediaStatus.processing.value}
    ]
    assert series_api.detail_calls == [202]
    assert series_api.season_calls == [(202, 1)]
    assert results == [
        {
            "tv_title": "Show 202",
            "tv_title_availability": "PROCESSING",
            "tv_season": "S01",
            "tv_season_availability": "PROCESSING",
            "tv_episodes": [{"episode_number": "01", "episode_name": "Pilot"}],
            "request_date": "2020-09-14T10:00:27.000Z",
        }
    ]
