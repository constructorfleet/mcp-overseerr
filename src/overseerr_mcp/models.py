"""Pydantic models for Overseerr MCP tool inputs."""

from __future__ import annotations

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
        description="Filter by media availability status.",
    )
    start_date: str | None = Field(
        default=None,
        description="Filter for the date of request, formatted as '2020-09-12T10:00:27.000Z'",
    )

    model_config = {
        "extra": "forbid",
    }


class TvRequestsFilter(BaseModel):
    """Filters for listing TV requests."""

    status: MediaStatus | None = Field(
        default=None,
        description="Filter by media availability status.",
    )
    start_date: str | None = Field(
        default=None,
        description="Filter for the date of request, formatted as '2020-09-12T10:00:27.000Z'",
    )

    model_config = {
        "extra": "forbid",
    }
