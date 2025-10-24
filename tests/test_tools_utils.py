"""Edge case tests for overseerr tools utility functions."""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

src_str = str(SRC_PATH)
if src_str not in sys.path:
    sys.path.append(src_str)

for key, value in {
    "OVERSEERR_API_KEY": "test",
    "OVERSEERR_URL": "http://localhost",
}.items():
    os.environ.setdefault(key, value)

from overseerr_mcp.tools import (
    _media_availability_from_status,
    _should_exclude_by_start_date,
    _to_plain,
    _parse_datetime,
    _normalize_to_utc,
)


def test_media_availability_returns_unknown_for_none_and_invalid():
    assert _media_availability_from_status(None) == "UNKNOWN"
    assert _media_availability_from_status("invalid") == "UNKNOWN"


@pytest.mark.parametrize(
    "normalized_start, created_at, expected",
    [
        (None, "2024-01-01T00:00:00Z", False),
        (
            datetime(2024, 1, 2, tzinfo=timezone.utc),
            "2024-01-01T00:00:00Z",
            True,
        ),
        (
            datetime(2024, 1, 2, tzinfo=timezone.utc),
            "",
            False,
        ),
    ],
)
def test_should_exclude_by_start_date_handles_missing_and_invalid_dates(
    normalized_start, created_at, expected
):
    assert _should_exclude_by_start_date(normalized_start, created_at) is expected


@dataclass
class _SampleDataclass:
    value: int
    labels: set[str]


class _HasToDict:
    def __init__(self, data: dict):
        self._data = data

    def to_dict(self):
        return self._data


class _SimpleObject:
    def __init__(self):
        self.answer = 42
        self.extra = _SampleDataclass(1, {"b", "a"})


def test_to_plain_flattens_dataclasses_and_sets_deterministically():
    plain = _to_plain(_SampleDataclass(5, {"beta", "alpha"}))
    assert plain == {"value": 5, "labels": ["alpha", "beta"]}


def test_to_plain_prefers_to_dict_over_dunder_dict():
    plain = _to_plain(_HasToDict({"nested": _SampleDataclass(2, {"x", "y"})}))
    assert plain == {"nested": {"value": 2, "labels": ["x", "y"]}}


def test_to_plain_uses_dunder_dict_when_available():
    plain = _to_plain(_SimpleObject())
    assert plain == {"answer": 42, "extra": {"value": 1, "labels": ["a", "b"]}}


def test_parse_datetime_returns_none_for_empty_or_invalid():
    assert _parse_datetime("") is None
    assert _parse_datetime("not-a-date") is None


def test_parse_datetime_normalizes_trailing_z_to_aware_datetime():
    parsed = _parse_datetime("2024-05-01T12:30:00Z")
    assert parsed == datetime(2024, 5, 1, 12, 30, tzinfo=timezone.utc)


def test_normalize_to_utc_handles_none_naive_and_offset():
    assert _normalize_to_utc(None) is None

    naive = datetime(2024, 5, 1, 12, 30)
    assert _normalize_to_utc(naive) == datetime(2024, 5, 1, 12, 30, tzinfo=timezone.utc)

    aware = datetime(2024, 5, 1, 8, 30, tzinfo=timezone(timedelta(hours=-4)))
    normalized = _normalize_to_utc(aware)
    assert normalized.tzinfo == timezone.utc
    assert normalized.hour == 12
