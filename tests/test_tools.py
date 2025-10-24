import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("OVERSEERR_API_KEY", "test")
os.environ.setdefault("OVERSEERR_URL", "http://localhost")

from overseerr_mcp.models import MediaRequestsFilter, MediaStatus, TvRequestsFilter
from overseerr_mcp.tools import MovieRequestsToolHandler, TvRequestsToolHandler


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
