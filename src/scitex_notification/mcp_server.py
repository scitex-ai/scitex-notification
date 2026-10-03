#!/usr/bin/env python3
# Timestamp: "2026-03-16 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/mcp_server.py

"""MCP Server for SciTeX Notifications - Multi-backend alert system.

Supports: audio, desktop, email, matplotlib, playwright, webhook backends.

Usage:
    scitex-notification mcp start
    python -m scitex_notification.mcp_server
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import scitex_logging as slogging

from . import __version__
from ._env_loader import load_scitex_notification_env as _load_env

log = slogging.getLogger(__name__)

_load_env()

# Graceful MCP dependency handling
try:
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    types = None  # type: ignore
    Server = None  # type: ignore
    NotificationOptions = None  # type: ignore
    InitializationOptions = None  # type: ignore
    stdio_server = None  # type: ignore

__all__ = ["NotifyServer", "main", "MCP_AVAILABLE"]


class NotifyServer:
    """MCP Server for multi-backend notifications."""

    def __init__(self):
        self.server = Server("scitex-notification")
        self._notification_count: int = 0
        self.setup_handlers()

    def setup_handlers(self):
        """Set up MCP server handlers."""
        from ._mcp.handlers import (
            available_backends_handler,
            get_config_handler,
            list_backends_handler,
            notify_by_level_handler,
            notify_handler,
            skills_get_handler,
            skills_list_handler,
        )
        from ._mcp.tool_schemas import get_tool_schemas

        @self.server.list_tools()
        async def handle_list_tools():
            return get_tool_schemas()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            if name == "notify":
                self._notification_count += 1
                return await notify_handler(**arguments)
            elif name == "notify_by_level":
                self._notification_count += 1
                return await notify_by_level_handler(**arguments)
            elif name == "list_notification_backends":
                return await list_backends_handler()
            elif name == "available_notification_backends":
                return await available_backends_handler()
            elif name == "get_notification_config":
                return await get_config_handler()
            elif name == "notification_skills_list":
                return await skills_list_handler()
            elif name == "notification_skills_get":
                return await skills_get_handler(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

        @self.server.list_resources()
        async def handle_list_resources():
            # Return notification statistics as a resource
            return [
                types.Resource(
                    uri="notify://stats",
                    name="Notification Statistics",
                    description="Current notification session statistics",
                    mimeType="application/json",
                )
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str):
            if uri == "notify://stats":
                from ._backends import available_backends
                from ._backends._config import get_config

                config = get_config()
                stats = {
                    "total_notifications": self._notification_count,
                    "available_backends": available_backends(),
                    "default_backend": config.default_backend,
                    "timestamp": datetime.now().isoformat(),
                }
                import json

                return types.ResourceContent(
                    uri=uri,
                    mimeType="application/json",
                    content=json.dumps(stats, indent=2),
                )
            raise ValueError(f"Unknown resource: {uri}")


async def _run_server():
    """Run the MCP server (internal)."""
    server = NotifyServer()
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="scitex-notification",
                server_version=__version__,
                capabilities=server.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main():
    """Run the MCP server."""
    if not MCP_AVAILABLE:
        import sys

        # PS-220: diagnostics via scitex-logging (stderr), not print.
        log.error("=" * 60)
        log.error("MCP Server 'scitex-notification' requires the 'mcp' package.")
        log.error("Install with:")
        log.error("  pip install mcp")
        log.error("Or install scitex-notification with MCP support:")
        log.error("  pip install scitex-notification[mcp]")
        log.error("=" * 60)
        sys.exit(1)

    asyncio.run(_run_server())


if __name__ == "__main__":
    main()


# EOF
