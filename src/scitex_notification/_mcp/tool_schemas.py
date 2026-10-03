#!/usr/bin/env python3
# Timestamp: "2026-03-16 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_mcp/tool_schemas.py

"""Tool schemas for the scitex-notification MCP server."""

from __future__ import annotations

# PS-233: `mcp` is an optional extra ([mcp]); keep this import guarded so a
# lean `pip install scitex-notification` still imports. All other `mcp`
# import sites are already guarded — this was the single unguarded site.
try:
    import mcp.types as types
except ImportError:
    types = None  # type: ignore[no-redef]

__all__ = ["get_tool_schemas"]


def get_tool_schemas() -> list[types.Tool]:  # type: ignore[name-defined]
    """Return all tool schemas for the notification MCP server."""
    if types is None:
        raise ImportError(
            "get_tool_schemas() needs the 'mcp' package: "
            "pip install scitex-notification[mcp]"
        )
    return [
        types.Tool(
            name="notify",
            description=(
                "Send an alert through any of 9 backends — `audio` (spoken TTS), "
                "`desktop` (OS popup), `emacs` (minibuffer), `matplotlib` (banner), "
                "`playwright` (browser toast), `email` (SMTP), `webhook` (HTTP "
                "POST), `telegram`, `twilio` (phone call / SMS) — with automatic "
                "fallback if a backend fails. Drop-in replacement for `smtplib`, "
                "`plyer.notification`, `requests.post(slack_webhook)`, "
                "`python-telegram-bot`. Use whenever the user asks to 'notify me', "
                "'alert me when this finishes', 'beep when done', 'email me the "
                "result', 'ping me on Telegram', 'send a desktop notification', or "
                "is wiring up monitoring from scripts / CI / AI agents. Pass "
                "`backend='email'` for a specific channel, or `backends=['audio', "
                "'email']` for multi-channel. `level` sets urgency (info / warning "
                "/ error / critical)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The notification message to send",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional notification title",
                    },
                    "level": {
                        "type": "string",
                        "description": "Notification urgency level",
                        "enum": ["info", "warning", "error", "critical"],
                        "default": "info",
                    },
                    "backend": {
                        "type": "string",
                        "description": (
                            "Backend to use (audio, desktop, email, matplotlib, "
                            "playwright, webhook). If not specified, uses default from config."
                        ),
                    },
                    "backends": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Multiple backends to use simultaneously",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout for visual backends (matplotlib, playwright)",
                        "default": 5.0,
                    },
                    "idempotency_key": {
                        "type": "string",
                        "description": (
                            "Caller-generated correlation key returned in the delivery "
                            "receipt. Backends report whether they enforce deduplication."
                        ),
                    },
                },
                "required": ["message"],
            },
        ),
        types.Tool(
            name="notify_by_level",
            description=(
                "Route a notification through whichever backend set the user has "
                "pre-configured for that urgency level — e.g. `info` → just emacs, "
                "`critical` → audio + desktop + email + Twilio phone call. Lets "
                "callers just say 'this is critical' and let the config decide how "
                "loudly to shout. Use whenever the user asks to 'alert at error "
                "level', 'escalate to critical', 'send a warning through my usual "
                "channels', or has set up `level_backends` in their scitex-"
                "notification config."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The notification message to send",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional notification title",
                    },
                    "level": {
                        "type": "string",
                        "description": "Notification level (determines which backends to use)",
                        "enum": ["info", "warning", "error", "critical"],
                        "default": "info",
                    },
                },
                "required": ["message"],
            },
        ),
        types.Tool(
            name="list_notification_backends",
            description=(
                "Enumerate every registered notification backend (audio, desktop, "
                "emacs, matplotlib, playwright, email, webhook, telegram, twilio) "
                "along with its reachability status — dependencies installed, env "
                "vars set, connections healthy. Use when the user asks 'which "
                "notifiers are set up?', 'why isn't my Twilio alert working?', "
                "'is email configured?', or is debugging a silent notification."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="available_notification_backends",
            description=(
                "List only the backends that are currently *working* — "
                "dependencies imported cleanly and credentials / env vars / "
                "sockets are intact. Shorter than `list_notification_backends` "
                "and the right check before picking a fallback order at runtime. "
                "Use when the user asks 'what notifiers actually work right "
                "now?', 'which backends are live?', or before programmatically "
                "choosing one."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_notification_config",
            description=(
                "Dump the active notification config — fallback order, per-"
                "level backend mapping (info/warning/error/critical → which "
                "backends), per-backend timeouts, Twilio/Telegram/webhook/email "
                "credentials (with secrets redacted). Use when the user asks "
                "'show my notification config', 'what's my fallback order?', "
                "'which backends fire for critical?', or is auditing before "
                "editing `~/.scitex/notification/config.yaml`."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        # §5 — skills introspection tools (per audit-mcp-tools convention)
        types.Tool(
            name="notification_skills_list",
            description=(
                "List the names of every skill page shipped by scitex-"
                "notification. Use whenever the user wants to discover what "
                "detailed docs exist (backends, configuration, CLI reference, "
                "MCP tools, Python API) before drilling into a specific topic. "
                "Returns a JSON envelope with `skills: [...]`."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="notification_skills_get",
            description=(
                "Fetch the full Markdown content of one scitex-notification "
                "skill page. Use after `notification_skills_list` to read an "
                "individual guide (e.g. `backends`, `configuration`, `cli-"
                "reference`, `mcp-tools`, `python-api`). Returns a JSON "
                "envelope with `content: <markdown>` or an error envelope "
                "listing available names."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Skill page name without `.md`, e.g. `backends`."
                        ),
                    }
                },
                "required": ["name"],
            },
        ),
    ]


# EOF
