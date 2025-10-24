"""Pydantic models for Overseerr MCP tool inputs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MediaStatus(str, Enum):
    """Available request status filters supported by Overseerr."""

    all = "all"
    approved = "approved"
    available = "available"
    pending = "pending"
    processing = "processing"
    unavailable = "unavailable"
    failed = "failed"


class StatusToolInput(BaseModel):
    """Empty input for the status tool."""

    model_config = {
        "extra": "forbid",
    }


class MediaRequestsFilter(BaseModel):
    """Filters for listing movie requests."""

    status: MediaStatus | None = Field(
        default=None,
        description=(
            "Limit results to requests matching the Overseerr status (approved, available, "
            "pending, processing, unavailable, failed)."
        ),
    )
    start_date: datetime | None = Field(
        default=None,
        description=(
            "Return requests created on or after the provided ISO 8601 timestamp "
            "(e.g. 2020-09-12T10:00:27Z)."
        ),
    )

    model_config = {
        "extra": "forbid",
    }


class TvRequestsFilter(BaseModel):
    """Filters for listing TV requests."""

    status: MediaStatus | None = Field(
        default=None,
        description=(
            "Limit results to requests matching the Overseerr status (approved, available, "
            "pending, processing, unavailable, failed)."
        ),
    )
    start_date: datetime | None = Field(
        default=None,
        description=(
            "Return requests created on or after the provided ISO 8601 timestamp "
            "(e.g. 2020-09-12T10:00:27Z)."
        ),
    )

    model_config = {
        "extra": "forbid",
    }
