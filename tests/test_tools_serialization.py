from dataclasses import dataclass
import os
from pathlib import Path
import sys

os.environ.setdefault("OVERSEERR_API_KEY", "test-key")
os.environ.setdefault("OVERSEERR_URL", "http://localhost")

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from overseerr_mcp.tools import _to_plain


@dataclass
class InnerSample:
    value: int


@dataclass
class OuterSample:
    name: str
    inner: InnerSample
    numbers: tuple[int, ...]
    tags: set[str]
    details: object


class DictLike:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_dict(self) -> dict:
        return self._payload


class Unsupported:
    __slots__ = ("value",)

    def __init__(self, value: str):
        self.value = value


def _assert_all_plain(value):
    if isinstance(value, dict):
        for item in value.values():
            _assert_all_plain(item)
        return
    if isinstance(value, list):
        for item in value:
            _assert_all_plain(item)
        return
    assert value is None or isinstance(value, (str, int, float, bool))


def test_to_plain_flattens_varied_structures_and_passthroughs_unknown():
    unsupported = Unsupported("marker")
    sample = {
        "outer": OuterSample(
            name="example",
            inner=InnerSample(42),
            numbers=(1, 2, 3),
            tags={"alpha", "gamma", "epsilon", "beta", "delta"},
            details=DictLike({"base": {"flag": True}}),
        ),
        "unsupported": unsupported,
    }

    result = _to_plain(sample)

    assert result["outer"]["name"] == "example"
    assert result["outer"]["inner"] == {"value": 42}
    assert result["outer"]["numbers"] == [1, 2, 3]
    assert result["outer"]["tags"] == ["alpha", "beta", "delta", "epsilon", "gamma"]
    assert result["outer"]["details"] == {"base": {"flag": True}}
    assert result["unsupported"] is unsupported
    assert result["unsupported"].value == "marker"

    _assert_all_plain(result["outer"])
