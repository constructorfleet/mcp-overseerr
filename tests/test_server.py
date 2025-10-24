import asyncio
import importlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))


def test_server_uses_overseerr_media_request_handler_name(monkeypatch):
    module_name = "overseerr_mcp.server"

    monkeypatch.setenv("OVERSEERR_API_KEY", "test")
    monkeypatch.setenv("OVERSEERR_URL", "http://localhost")

    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    module = importlib.reload(module)

    assert module.app.name == "Overseerr Media Request Handler"


def _reload_server(monkeypatch):
    module_name = "overseerr_mcp.server"

    monkeypatch.setenv("OVERSEERR_API_KEY", "test")
    monkeypatch.setenv("OVERSEERR_URL", "http://localhost")

    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    return importlib.reload(module)


def test_overseerr_status_invokes_status_handler(monkeypatch):
    module = _reload_server(monkeypatch)
    calls = {}

    async def fake_run_tool(args):
        calls["args"] = args
        return [SimpleNamespace(text="status response")]

    monkeypatch.setattr(module, "status_tool_handler", SimpleNamespace(run_tool=fake_run_tool))

    result = asyncio.run(module.overseerr_status())

    assert calls["args"] == {}
    assert result == "status response"


def test_overseerr_movie_requests_invokes_movie_handler(monkeypatch):
    module = _reload_server(monkeypatch)
    calls = {}

    async def fake_run_tool(args):
        calls["args"] = args
        return [SimpleNamespace(text="movie response")]

    monkeypatch.setattr(module, "movie_requests_tool_handler", SimpleNamespace(run_tool=fake_run_tool))

    result = asyncio.run(module.overseerr_movie_requests(status="approved", start_date="2024-01-01"))

    assert calls["args"] == {"status": "approved", "start_date": "2024-01-01"}
    assert result == "movie response"


def test_overseerr_tv_requests_invokes_tv_handler(monkeypatch):
    module = _reload_server(monkeypatch)
    calls = {}

    async def fake_run_tool(args):
        calls["args"] = args
        return [SimpleNamespace(text="tv response")]

    monkeypatch.setattr(module, "tv_requests_tool_handler", SimpleNamespace(run_tool=fake_run_tool))

    result = asyncio.run(module.overseerr_tv_requests(status="pending", start_date="2024-02-01"))

    assert calls["args"] == {"status": "pending", "start_date": "2024-02-01"}
    assert result == "tv response"


def test_server_import_requires_environment_variables(monkeypatch):
    module_name = "overseerr_mcp.server"

    monkeypatch.delenv("OVERSEERR_API_KEY", raising=False)
    monkeypatch.delenv("OVERSEERR_URL", raising=False)

    sys.modules.pop(module_name, None)

    with pytest.raises(ValueError):
        importlib.import_module(module_name)
