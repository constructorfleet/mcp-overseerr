"""Overseerr MCP package exports."""

from . import models, server


def main() -> None:
    """Entry point for the overseerr-mcp command."""

    server.main()


__all__ = ["main", "server", "models"]
