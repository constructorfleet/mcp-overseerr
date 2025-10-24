import importlib
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))


def test_server_uses_overseerr_media_request_handler_name(monkeypatch):
    module_name = "overseerr_mcp.server"

    monkeypatch.setenv("OVERSEERR_API_KEY", "test")
    monkeypatch.setenv("OVERSEERR_URL", "http://localhost")

    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    module = importlib.reload(module)

    assert module.app.name == "Overseerr Media Request Handler"
