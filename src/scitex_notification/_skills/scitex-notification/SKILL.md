---
name: scitex-notification
description: |
  [WHAT] One-call alerting across 9 backends — audio TTS (spoken notification), desktop popup, emacs minibuffer, matplotlib banner, playwright browser toast, email (SMTP), webhook (HTTP POST), Telegram message, and Twilio phone call / SMS — with automatic fallback (default order: audio → emacs → matplotlib → playwright → email) and level-based routing (info / warning / error / critical can trigger…
  [WHEN] Use whenever the user asks to "notify me when this finishes", "alert me if training fails", "send me an email when done", "call my phone if the server goes down", "text me the result", "push a Telegram message", "beep when the job completes", "escalate to phone call on critical errors", "ping Slack / webhook", or is wiring up notifications from scripts, pipelines, or AI agents.
  [HOW] See sub-skills index for entry points.
tags: [scitex-notification]
allowed-tools: mcp__scitex__notification_*
primary_interface: cli
interfaces:
  python: 0
  cli: 0
  mcp: 0
  skills: 0
  http: 0
---

# scitex-notification

Multi-backend alerting with automatic fallback. One `alert()` covers local and remote delivery.

## Sub-skills

### Mandatory leaves
* [01_installation](01_installation.md) — pip install + extras + smoke verify
* [02_quick-start](02_quick-start.md) — `alert()` with default fallback + Twilio
* [03_python-api](03_python-api.md) — top-level Python surface
* [04_cli-reference](04_cli-reference.md) — `scitex-notification` subcommand summary

### Reference
* [05_backends](05_backends.md) — per-backend setup, env vars, availability checks
* [06_python-api](06_python-api.md) — `alert()`, `call()`, `sms()` signatures, backends table (legacy detail)
* [07_mcp-tools](07_mcp-tools.md) — MCP tool schemas
* [08_configuration](08_configuration.md) — YAML config, `UIConfig`, level-based routing

### Environment
* [20_env-vars](20_env-vars.md) — `SCITEX_NOTIFICATION_*` env vars

## Quick Start

```python
import scitex_notification as stxn

# Simple alert — fallback: audio -> emacs -> matplotlib -> playwright -> email
stxn.alert("Training complete!")

# Specific backend, no fallback
stxn.alert("Error in pipeline", backend="email", level="error")

# Multiple backends simultaneously
stxn.alert("Critical!", backend=["audio", "email"])

# Phone call via Twilio (requires SCITEX_NOTIFICATION_TWILIO_* env vars)
stxn.call("Wake up! Server is down!")

# SMS via Twilio
stxn.sms("Build finished successfully")
```

## CLI

```bash
scitex-notification send-notification "Task done!"
scitex-notification call "Wake up!" --repeat 2
scitex-notification send-sms "Build complete"
scitex-notification list-backends     # List available backends
scitex-notification show-config       # Show configuration
scitex-notification mcp start         # Start MCP stdio server
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `notify` | Send alert via one or more backends with fallback |
| `notify_by_level` | Route by info / warning / error / critical to configured backend sets |
| `list_notification_backends` | List every registered backend with status |
| `available_notification_backends` | List backends that are currently working (deps + creds OK) |
| `get_notification_config` | Show active config (fallback order, level routing, timeouts) |

> Note: `call()` (Twilio phone) and `sms()` (Twilio SMS) are exposed via the Python API and CLI, not as standalone MCP tools. They reach through `notify` when `backend="twilio"`.
