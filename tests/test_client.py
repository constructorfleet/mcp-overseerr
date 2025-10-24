import asyncio
import importlib
import os
import sys
import types
from pathlib import Path

import pydantic  # noqa: F401

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("OVERSEERR_API_KEY", "test")
os.environ.setdefault("OVERSEERR_URL", "http://localhost")

def _install_fake_overseerr(monkeypatch):
    class FakeConfiguration:
        def __init__(self):
            self.host = None
            self.api_key = {}

    class FakeApiClient:
        def __init__(self, configuration):
            self.configuration = configuration

    class FakePublicApi:
        def __init__(self, client):
            self.client = client
            self.calls = []

        def get_status(self):
            self.calls.append("status")
            return {"status": "ok"}

    class FakeRequestApi:
        def __init__(self, client):
            self.client = client

        def get_request(self, *args, **kwargs):
            raise NotImplementedError

    class FakeMoviesApi:
        def __init__(self, client):
            self.client = client

        def get_movie_by_movie_id(self, movie_id):
            raise NotImplementedError

    class FakeTvApi:
        def __init__(self, client):
            self.client = client

        def get_tv_by_tv_id(self, tv_id):
            raise NotImplementedError

        def get_tv_season_by_season_id(self, request):
            raise NotImplementedError

    fake_module = types.SimpleNamespace(
        Configuration=FakeConfiguration,
        ApiClient=FakeApiClient,
        PublicApi=FakePublicApi,
        RequestApi=FakeRequestApi,
        MoviesApi=FakeMoviesApi,
        TvApi=FakeTvApi,
    )

    monkeypatch.setitem(sys.modules, "overseerr", fake_module)
    return fake_module


def test_overseerr_apis_uses_sdk_configuration(monkeypatch):
    _install_fake_overseerr(monkeypatch)

    captured_to_thread = {}

    async def fake_to_thread(func, *args, **kwargs):
        captured_to_thread["func"] = func
        captured_to_thread["args"] = args
        captured_to_thread["kwargs"] = kwargs
        return {"status": "ok"}

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    client_module = importlib.reload(importlib.import_module("overseerr_mcp.client"))

    apis = client_module.OverseerrApis(base_url="http://example", api_key="abc123")

    result = asyncio.run(apis.get_status())

    assert result == {"status": "ok"}

    assert captured_to_thread["func"].__self__.__class__.__name__ == "FakePublicApi"
    assert apis._config.host == "http://example/api/v1"
    assert apis._config.api_key["apiKey"] == "abc123"
    assert captured_to_thread["args"] == ()
    assert captured_to_thread["kwargs"] == {}
