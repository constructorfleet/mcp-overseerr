import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
 
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("OVERSEERR_API_KEY", "test")
os.environ.setdefault("OVERSEERR_URL", "http://localhost")

from overseerr import models
from overseerr_mcp.models import MediaRequestsFilter, MediaStatus, TvRequestsFilter
from overseerr_mcp.tools import (
    MovieRequestsToolHandler,
    StatusToolHandler,
    TvRequestsToolHandler,
)



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
            self.movie_calls = []

        async def get_requests(self, *, take: int, skip: int, filter: str | None = None):
            self.request_params.append({"take": take, "skip": skip, "filter": filter})
            self.request_calls += 1
            return models.GetUserRequests2XXResponse(
                results=[
                    models.MediaRequest(
                        id=1,
                        status=2,
                        created_at="2020-09-13T10:00:27.000Z",
                        media=models.MediaInfo(tmdb_id=1, status=2),
                    ),
                    models.MediaRequest(
                        id=2,
                        status=3,
                        created_at="2020-09-11T10:00:27.000Z",
                        media=models.MediaInfo(tmdb_id=2, status=5),
                    ),
                ],
                page_info=models.PageInfo(pages=1),
            )

        async def get_movie_by_movie_id(self, movie_id: int):
            self.movie_calls.append(movie_id)
            return models.MovieDetails(title=f"movie-{movie_id}")

        async def aclose(self):
            return None

    fake_client = FakeClient()

    monkeypatch.setattr(
        "overseerr_mcp.tools.OverseerrApis",
        lambda *args, **kwargs: fake_client,
    )

    results = asyncio.run(
        handler.get_movie_requests(
            status=MediaStatus.pending,
            start_date=datetime(2020, 9, 12, 10, 0, 27, tzinfo=timezone.utc),
        )
    )

    assert fake_client.request_params[0]["filter"] == "pending"
    assert fake_client.movie_calls == [1]
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


def test_tv_requests_excludes_entries_before_start_date():
    start_date = datetime(2020, 9, 12, 0, 0, tzinfo=timezone.utc)

    def make_request(request_id: int, *, tmdb_id: int, created_at: str):
        return models.MediaRequest(
            id=request_id,
            status=3,
            created_at=created_at,
            media=models.MediaInfo(
                tmdb_id=tmdb_id,
                tvdb_id=tmdb_id,
                status=3,
            ),
        )

    class FakeOverseerrApis:
        def __init__(self):
            self.tv_calls: list[int] = []
            self.season_calls: list[tuple[int, int]] = []

        async def get_requests(self, *, take: int, skip: int, filter: str | None = None):
            return models.GetUserRequests2XXResponse(
                results=[
                    make_request(1, tmdb_id=301, created_at="2020-09-10T05:00:00.000Z"),
                    make_request(2, tmdb_id=302, created_at="2020-09-12T05:00:00.000Z"),
                    make_request(3, tmdb_id=303, created_at="2020-09-15T05:00:00.000Z"),
                ],
                page_info=models.PageInfo(pages=1),
            )

        async def get_movie_by_movie_id(self, movie_id: int):
            raise AssertionError("Movie API should not be called for TV requests")

        async def get_tv_by_tv_id(self, tv_id: int):
            self.tv_calls.append(tv_id)
            return models.TvDetails(
                name=f"Show {tv_id}",
                seasons=[models.Season(season_number=1)],
            )

        async def get_tv_season_by_season_id(self, tv_id: int, season_number: int):
            self.season_calls.append((tv_id, season_number))
            return models.Season(
                season_number=season_number,
                episodes=[
                    models.Episode(
                        episode_number=1,
                        name=f"Episode {tv_id}-{season_number}",
                    )
                ],
            )

        async def aclose(self):
            return None

    fake_client = FakeOverseerrApis()

    handler = TvRequestsToolHandler(overseerr_factory=lambda: fake_client)

    results = asyncio.run(
        handler.get_tv_requests(
            status=MediaStatus.processing,
            start_date=start_date,
        )
    )

    assert [result["request_date"] for result in results] == [
        "2020-09-12T05:00:00.000Z",
        "2020-09-15T05:00:00.000Z",
    ]
    assert fake_client.tv_calls == [302, 303]
    assert fake_client.season_calls == [(302, 1), (303, 1)]
    assert results == [
        {
            "tv_title": "Show 302",
            "tv_title_availability": "PROCESSING",
            "tv_season": "S01",
            "tv_season_availability": "PROCESSING",
            "tv_episodes": [
                {"episode_number": "01", "episode_name": "Episode 302-1"}
            ],
            "request_date": "2020-09-12T05:00:00.000Z",
        },
        {
            "tv_title": "Show 303",
            "tv_title_availability": "PROCESSING",
            "tv_season": "S01",
            "tv_season_availability": "PROCESSING",
            "tv_episodes": [
                {"episode_number": "01", "episode_name": "Episode 303-1"}
            ],
            "request_date": "2020-09-15T05:00:00.000Z",
        },
    ]


def test_tv_requests_returns_results_when_start_date_missing():
    def make_request(request_id: int, *, tmdb_id: int, created_at: str):
        return models.MediaRequest(
            id=request_id,
            status=3,
            created_at=created_at,
            media=models.MediaInfo(
                tmdb_id=tmdb_id,
                tvdb_id=tmdb_id,
                status=3,
            ),
        )

    class FakeOverseerrApis:
        def __init__(self):
            self.tv_calls: list[int] = []
            self.season_calls: list[tuple[int, int]] = []

        async def get_requests(self, *, take: int, skip: int, filter: str | None = None):
            requests = [
                make_request(1, tmdb_id=401, created_at="2020-09-10T05:00:00.000Z"),
                make_request(2, tmdb_id=402, created_at="2020-09-12T05:00:00.000Z"),
            ]

            return models.GetUserRequests2XXResponse(
                results=requests,
                page_info=models.PageInfo(pages=1),
            )

        async def get_movie_by_movie_id(self, movie_id: int):
            raise AssertionError("Movie API should not be called for TV requests")

        async def get_tv_by_tv_id(self, tv_id: int):
            self.tv_calls.append(tv_id)
            return models.TvDetails(
                name=f"Show {tv_id}",
                seasons=[models.Season(season_number=1)],
            )

        async def get_tv_season_by_season_id(self, tv_id: int, season_number: int):
            self.season_calls.append((tv_id, season_number))
            return models.Season(
                season_number=season_number,
                episodes=[
                    models.Episode(
                        episode_number=1,
                        name=f"Episode {tv_id}-{season_number}",
                    )
                ],
            )

        async def aclose(self):
            return None

    fake_client = FakeOverseerrApis()

    handler = TvRequestsToolHandler(overseerr_factory=lambda: fake_client)

    results = asyncio.run(
        handler.get_tv_requests(
            status=MediaStatus.processing,
            start_date=None,
        )
    )

    assert [result["request_date"] for result in results] == [
        "2020-09-10T05:00:00.000Z",
        "2020-09-12T05:00:00.000Z",
    ]
    assert fake_client.tv_calls == [401, 402]
    assert fake_client.season_calls == [(401, 1), (402, 1)]
    assert results == [
        {
            "tv_title": "Show 401",
            "tv_title_availability": "PROCESSING",
            "tv_season": "S01",
            "tv_season_availability": "PROCESSING",
            "tv_episodes": [
                {"episode_number": "01", "episode_name": "Episode 401-1"}
            ],
            "request_date": "2020-09-10T05:00:00.000Z",
        },
        {
            "tv_title": "Show 402",
            "tv_title_availability": "PROCESSING",
            "tv_season": "S01",
            "tv_season_availability": "PROCESSING",
            "tv_episodes": [
                {"episode_number": "01", "episode_name": "Episode 402-1"}
            ],
            "request_date": "2020-09-12T05:00:00.000Z",
        },
    ]

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

def test_iter_request_pages_yields_each_page():
    from overseerr_mcp.tools import _iter_request_pages

    first_page = models.GetUserRequests2XXResponse(
        results=[
            models.MediaRequest(
                id=1,
                status=2,
                created_at="2020-09-13T10:00:27.000Z",
                media=models.MediaInfo(tmdb_id=1, status=2),
            )
        ],
        page_info=models.PageInfo(pages=2),
    )
    second_page = models.GetUserRequests2XXResponse(
        results=[],
        page_info=models.PageInfo(pages=2),
    )

    class FakeClient:
        def __init__(self):
            self.calls: list[dict[str, Any]] = []
            self._pages = [first_page, second_page]

        async def get_requests(self, *, take: int, skip: int, filter: str | None = None):
            self.calls.append({"take": take, "skip": skip, "filter": filter})
            return self._pages.pop(0)

    fake_client = FakeClient()

    async def collect():
        pages = []
        async for page in _iter_request_pages(fake_client, status_filter="pending"):
            pages.append(page)
        return pages

    pages = asyncio.run(collect())

    assert [call["skip"] for call in fake_client.calls] == [0, 20]
    assert len(pages) == 2
    assert pages[0].results[0].media.status == 2


def test_iter_request_pages_returns_pydantic_models():
    from overseerr import models
    from overseerr_mcp.tools import _iter_request_pages

    first_page = models.GetUserRequests2XXResponse(
        page_info=models.PageInfo(pages=2),
        results=[
            models.MediaRequest(
                id=1,
                status=2,
                created_at="2020-09-13T10:00:27.000Z",
                media=models.MediaInfo(tmdb_id=123, status=5),
            )
        ],
    )
    second_page = models.GetUserRequests2XXResponse(
        page_info=models.PageInfo(pages=2),
        results=[],
    )

    class FakeClient:
        def __init__(self):
            self._pages = [first_page, second_page]

        async def get_requests(self, *, take: int, skip: int, filter: str | None = None):
            return self._pages.pop(0)

    fake_client = FakeClient()

    async def collect():
        pages = []
        async for page in _iter_request_pages(fake_client, status_filter=None):
            pages.append(page)
        return pages

    pages = asyncio.run(collect())

    assert all(isinstance(page, models.GetUserRequests2XXResponse) for page in pages)
    assert pages[0].results[0].media.tmdb_id == 123


def test_movie_requests_handler_uses_sdk_factory():
    class FakeOverseerrApis:
        def __init__(self):
            self.request_calls: list[dict[str, Any]] = []
            self.movie_calls: list[int] = []

        async def get_requests(self, *, take: int, skip: int, filter: str | None = None):
            self.request_calls.append({"take": take, "skip": skip, "filter": filter})
            return models.GetUserRequests2XXResponse(
                results=[
                    models.MediaRequest(
                        id=101,
                        status=2,
                        created_at="2020-09-13T10:00:27.000Z",
                        media=models.MediaInfo(tmdb_id=101, status=5),
                    )
                ],
                page_info=models.PageInfo(pages=1),
            )

        async def get_movie_by_movie_id(self, movie_id: int):
            self.movie_calls.append(movie_id)
            return models.MovieDetails(title="Movie 101")

        async def get_tv_by_tv_id(self, tv_id: int):
            raise AssertionError("TV API should not be called for movie requests")

        async def get_tv_season_by_season_id(self, request):
            raise AssertionError("TV season API should not be called for movie requests")

        async def aclose(self):
            return None

    fake_client = FakeOverseerrApis()

    handler = MovieRequestsToolHandler(overseerr_factory=lambda: fake_client)

    results = asyncio.run(handler.get_movie_requests(status=MediaStatus.available))

    assert results == [
        {
            "title": "Movie 101",
            "media_availability": "AVAILABLE",
            "request_date": "2020-09-13T10:00:27.000Z",
        }
    ]


def test_tv_requests_handler_fetches_season_details():
    tv_request = models.MediaRequest(
        id=202,
        status=2,
        created_at="2020-09-14T10:00:27.000Z",
        media=models.MediaInfo(tmdb_id=202, tvdb_id=555, status=3),
    )
    class FakeOverseerrApis:
        def __init__(self):
            self.request_calls: list[dict[str, Any]] = []
            self.tv_calls: list[int] = []
            self.season_calls: list[tuple[int, int]] = []

        async def get_requests(self, *, take: int, skip: int, filter: str | None = None):
            self.request_calls.append({"take": take, "skip": skip, "filter": filter})
            return models.GetUserRequests2XXResponse(
                results=[tv_request],
                page_info=models.PageInfo(pages=1),
            )

        async def get_movie_by_movie_id(self, movie_id: int):
            raise AssertionError("Movie API should not be called for TV requests")

        async def get_tv_by_tv_id(self, tv_id: int):
            self.tv_calls.append(tv_id)
            return models.TvDetails(
                name="Show 202",
                seasons=[
                    models.Season(season_number=0),
                    models.Season(season_number=1),
                ],
            )

        async def get_tv_season_by_season_id(self, *args, **kwargs):
            self.season_calls.append((args, kwargs))
            return models.Season(
                season_number=1,
                episodes=[models.Episode(episode_number=1, name="Pilot")],
            )

        async def aclose(self):
            return None

    fake_client = FakeOverseerrApis()

    handler = TvRequestsToolHandler(overseerr_factory=lambda: fake_client)

    results = asyncio.run(handler.get_tv_requests(status=MediaStatus.processing))

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


def test_status_handler_reports_successful_status():
    handler = StatusToolHandler(overseerr_factory=lambda: _FakeStatusClient({"version": "1.2.3"}))

    async def invoke():
        return await handler.run_tool({})

    response = asyncio.run(invoke())

    assert len(response) == 1
    assert response[0].text == (
        "\n---\nOverseerr is available and these are the status data:\n"
        "\n- version: 1.2.3\n"
    )


def test_status_handler_reports_error_payload():
    handler = StatusToolHandler(
        overseerr_factory=lambda: _FakeStatusClient({"error": "Gateway Timeout"})
    )

    async def invoke():
        return await handler.run_tool({})

    response = asyncio.run(invoke())

    assert len(response) == 1
    assert response[0].text == (
        "\n---\nOverseerr is not available and below is the request error: \n"
        "\n- error: Gateway Timeout\n"
    )


def test_status_handler_handles_non_dict_status():
    handler = StatusToolHandler(
        overseerr_factory=lambda: _FakeStatusClient("503 Service Unavailable")
    )

    async def invoke():
        return await handler.run_tool({})

    response = asyncio.run(invoke())

    assert len(response) == 1
    assert response[0].text == (
        "\n---\nOverseerr is not available and below is the request error: \n"
        "\n- 503 Service Unavailable\n"
    )


class _FakeStatusClient:
    def __init__(self, payload):
        self._payload = payload

    async def get_status(self):
        return self._payload

    async def aclose(self):
        return None
