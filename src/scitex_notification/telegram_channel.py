#!/usr/bin/env python3
# Timestamp: "2026-03-22 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/telegram_channel.py

"""Telegram Channel MCP Server for Claude Code.

A two-way channel that bridges Telegram messages into Claude Code sessions.
Researchers message @scitex_ai_bot on Telegram, Claude Code processes using
SciTeX MCP tools, and replies go back through Telegram.

Uses Claude Code's native Channels feature (experimental).

Usage:
    scitex-notification telegram-channel start

    # In Claude Code MCP config:
    {
        "mcpServers": {
            "telegram": {
                "command": "scitex-notification",
                "args": ["telegram-channel", "start"],
                "env": {
                    "SCITEX_NOTIFICATION_TELEGRAM_TOKEN": "your-bot-token",
                    "SCITEX_NOTIFICATION_TELEGRAM_CHAT_ID": "your-chat-id"
                }
            }
        }
    }

    # Start Claude Code with the channel:
    claude --dangerously-load-development-channels server:telegram
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

import scitex_logging as slogging

from ._env_loader import load_scitex_notification_env as _load_env

log = slogging.getLogger(__name__)

_load_env()

try:
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"

CHANNEL_INSTRUCTIONS = """\
Messages from Telegram arrive as <channel source="telegram" chat_id="..." sender="...">.
Reply using the telegram_reply tool, passing the chat_id from the tag.
For images, use telegram_send_photo with a local file path.
For documents, use telegram_send_document with a local file path.
The user is a researcher — explain results in plain language with statistics.
"""


def _telegram_api(token: str, method: str, data: dict | None = None) -> dict:
    """Make a Telegram Bot API JSON request."""
    url = f"{TELEGRAM_API_BASE.format(token=token)}/{method}"
    body = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read().decode())
    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result.get('description', 'unknown')}"
        )
    return result


def _telegram_multipart(
    token: str, method: str, fields: dict, file_field: str, file_path: str
) -> dict:
    """Telegram Bot API multipart upload."""
    boundary = "----ScitexChannelBoundary"
    body = b""
    for key, value in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()
    filename = Path(file_path).name
    body += f"--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"\r\n'
    ).encode()
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += Path(file_path).read_bytes()
    body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    url = f"{TELEGRAM_API_BASE.format(token=token)}/{method}"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read().decode())
    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result.get('description', 'unknown')}"
        )
    return result


class TelegramChannelServer:
    """Two-way Telegram channel for Claude Code."""

    def __init__(self):
        self.token = os.getenv("SCITEX_NOTIFICATION_TELEGRAM_TOKEN", "")
        self.allowed_chat_id = os.getenv("SCITEX_NOTIFICATION_TELEGRAM_CHAT_ID", "")
        self._last_update_id = 0
        self._polling_task: asyncio.Task | None = None
        self._polling_enabled = (
            os.getenv("SCITEX_NOTIFICATION_TELEGRAM_POLLING_ENABLED", "false").lower()
            == "true"
        )

        self.server = Server(
            name="telegram",
            instructions=CHANNEL_INSTRUCTIONS,
        )
        self._setup_tools()

    def _setup_tools(self):
        """Register reply tools for bidirectional communication."""

        @self.server.list_tools()
        async def handle_list_tools():
            return [
                types.Tool(
                    name="telegram_reply",
                    description="Send a text message back to a Telegram chat",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "string",
                                "description": "The chat_id from the inbound channel tag",
                            },
                            "text": {
                                "type": "string",
                                "description": "The message text to send",
                            },
                        },
                        "required": ["chat_id", "text"],
                    },
                ),
                types.Tool(
                    name="telegram_send_photo",
                    description="Send an image file to a Telegram chat",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "string",
                                "description": "The chat_id from the inbound channel tag",
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Local path to the image file",
                            },
                            "caption": {
                                "type": "string",
                                "description": "Optional caption for the image",
                            },
                        },
                        "required": ["chat_id", "file_path"],
                    },
                ),
                types.Tool(
                    name="telegram_send_document",
                    description="Send a document/file to a Telegram chat",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "string",
                                "description": "The chat_id from the inbound channel tag",
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Local path to the file",
                            },
                            "caption": {
                                "type": "string",
                                "description": "Optional caption for the document",
                            },
                        },
                        "required": ["chat_id", "file_path"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            if name == "telegram_reply":
                return await self._reply_text(arguments["chat_id"], arguments["text"])
            elif name == "telegram_send_photo":
                return await self._reply_photo(
                    arguments["chat_id"],
                    arguments["file_path"],
                    arguments.get("caption", ""),
                )
            elif name == "telegram_send_document":
                return await self._reply_document(
                    arguments["chat_id"],
                    arguments["file_path"],
                    arguments.get("caption", ""),
                )
            raise ValueError(f"Unknown tool: {name}")

    async def _reply_text(self, chat_id: str, text: str) -> list[types.TextContent]:
        """Send a text reply to Telegram."""
        # Telegram limit: 4096 chars per message
        loop = asyncio.get_event_loop()
        for i in range(0, len(text), 4000):
            chunk = text[i : i + 4000]
            await loop.run_in_executor(
                None,
                lambda c=chunk: _telegram_api(
                    self.token,
                    "sendMessage",
                    {"chat_id": chat_id, "text": c},
                ),
            )
        return [types.TextContent(type="text", text="sent")]

    async def _reply_photo(
        self, chat_id: str, file_path: str, caption: str
    ) -> list[types.TextContent]:
        """Send a photo to Telegram."""
        if not Path(file_path).exists():
            return [types.TextContent(type="text", text=f"File not found: {file_path}")]
        loop = asyncio.get_event_loop()
        fields = {"chat_id": chat_id}
        if caption:
            fields["caption"] = caption[:1024]
        await loop.run_in_executor(
            None,
            lambda: _telegram_multipart(
                self.token, "sendPhoto", fields, "photo", file_path
            ),
        )
        return [
            types.TextContent(type="text", text=f"photo sent: {Path(file_path).name}")
        ]

    async def _reply_document(
        self, chat_id: str, file_path: str, caption: str
    ) -> list[types.TextContent]:
        """Send a document to Telegram."""
        if not Path(file_path).exists():
            return [types.TextContent(type="text", text=f"File not found: {file_path}")]
        loop = asyncio.get_event_loop()
        fields = {"chat_id": chat_id}
        if caption:
            fields["caption"] = caption[:1024]
        await loop.run_in_executor(
            None,
            lambda: _telegram_multipart(
                self.token, "sendDocument", fields, "document", file_path
            ),
        )
        return [
            types.TextContent(
                type="text", text=f"document sent: {Path(file_path).name}"
            )
        ]

    async def _poll_telegram(self):
        """Poll Telegram for new messages and push as channel events."""
        loop = asyncio.get_event_loop()
        while True:
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: _telegram_api(
                        self.token,
                        "getUpdates",
                        {
                            "offset": self._last_update_id + 1,
                            "timeout": 10,
                        },
                    ),
                )
                for update in result.get("result", []):
                    self._last_update_id = update["update_id"]
                    message = update.get("message")
                    if not message:
                        continue

                    chat_id = str(message["chat"]["id"])
                    # Gate on allowed sender
                    if self.allowed_chat_id and chat_id != self.allowed_chat_id:
                        continue

                    sender = message.get("from", {})
                    sender_name = f"{sender.get('first_name', '')} {sender.get('last_name', '')}".strip()
                    text = message.get("text", "")

                    if not text:
                        continue

                    # Push as channel event
                    await self.server.request_context.session.send_notification(
                        types.ServerNotification(
                            method="notifications/claude/channel",
                            params=types.ServerNotificationParams(
                                content=text,
                                meta={
                                    "chat_id": chat_id,
                                    "sender": sender_name,
                                },
                            ),
                        )
                    )

            except Exception:
                await asyncio.sleep(2)

            await asyncio.sleep(1)

    async def run(self):
        """Run the Telegram channel MCP server."""
        if not self.token:
            raise ValueError(
                "SCITEX_NOTIFICATION_TELEGRAM_TOKEN env var required. "
                "Get a token from @BotFather on Telegram."
            )

        async with stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name="telegram",
                server_version="0.1.0",
                capabilities=types.ServerCapabilities(
                    experimental={"claude/channel": {}},
                    tools=types.ToolsCapability(listChanged=False),
                ),
            )

            # Start polling in background (disabled by default — orochi-server owns Telegram polling)
            if self._polling_enabled:
                self._polling_task = asyncio.create_task(self._poll_telegram())

            await self.server.run(read_stream, write_stream, init_options)


def main():
    """Entry point for the Telegram channel server."""
    if not MCP_AVAILABLE:
        import sys

        # PS-220: diagnostics via scitex-logging (stderr), not print.
        log.error("Telegram channel requires the 'mcp' package.")
        log.error("Install with: pip install mcp")
        sys.exit(1)

    server = TelegramChannelServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()


# EOF
