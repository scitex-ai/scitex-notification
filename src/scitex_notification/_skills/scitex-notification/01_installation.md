---
description: |
  [TOPIC] scitex-notification Installation
  [DETAILS] pip install scitex-notification with optional [audio], [mcp], [playwright], [twilio], [all] extras; smoke verify.
tags: [scitex-notification-installation]
---

# Installation

## Standard

```bash
pip install scitex-notification
```

## Optional extras

| Extra        | Adds                                            |
|--------------|-------------------------------------------------|
| `audio`      | scitex-audio (TTS spoken notifications)         |
| `mcp`        | mcp (expose tools to AI agents)                 |
| `playwright` | playwright (browser-popup backend)              |
| `twilio`     | twilio (phone call + SMS backends)              |
| `all`        | every extra above                               |

```bash
pip install 'scitex-notification[audio,twilio]'
pip install 'scitex-notification[all]'
```

A few backends rely on system tools (emacsclient, matplotlib display).
SMTP / webhook / Telegram backends need credentials in env vars — see
`20_env-vars.md`.

## Verify

```bash
python -c "import scitex_notification; print(scitex_notification.__version__)"
scitex-notification --help
scitex-notification list-backends
```
