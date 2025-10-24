from datetime import datetime
import os
from pathlib import Path
from types import NoneType, UnionType
from typing import get_args, get_origin
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("OVERSEERR_API_KEY", "test")
os.environ.setdefault("OVERSEERR_URL", "http://localhost")


def test_status_tool_input_has_no_fields():
    from overseerr_mcp import models

    assert models.StatusToolInput.model_fields == {}


def test_media_status_enum_matches_existing_schema():
    from overseerr_mcp import models

    expected_values = [
        "all",
        "approved",
        "available",
        "pending",
        "processing",
        "unavailable",
        "failed",
    ]

    assert [member.value for member in models.MediaStatus] == expected_values


def test_media_filters_expose_expected_field_metadata():
    from overseerr_mcp import models

    for field_map in (
        models.MediaRequestsFilter.model_fields,
        models.TvRequestsFilter.model_fields,
    ):
        status_field = field_map["status"]
        start_date_field = field_map["start_date"]

        assert status_field.description == "Filter by media availability status."
        assert start_date_field.description == (
            "Filter for the date of request, formatted as '2020-09-12T10:00:27.000Z'"
        )

        status_annotation = status_field.annotation
        status_origin = get_origin(status_annotation)
        status_args = get_args(status_annotation)

        assert status_origin is UnionType
        assert models.MediaStatus in status_args
        assert NoneType in status_args

        start_annotation = start_date_field.annotation
        start_origin = get_origin(start_annotation)
        start_args = get_args(start_annotation)

        assert start_origin is UnionType
        assert datetime in start_args
        assert NoneType in start_args
