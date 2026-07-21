---
description: |
  [TOPIC] scitex-notification Quick Start
  [DETAILS] Smallest useful example — `alert()` with default fallback, plus phone call and SMS via Twilio.
tags: [scitex-notification-quick-start]
---

# Quick Start

## One-call alert

```python
import scitex_notification as stxn

stxn.alert("Training complete!")
```

Default fallback order: `audio → emacs → matplotlib → playwright → email`.
The first available backend wins; no exception if all fail (errors are
logged).

## Specific backend, no fallback

```python
stxn.alert("Pipeline error", backend="email", level="error")
```

## Multiple backends simultaneously

```python
stxn.alert("Critical!", backend=["audio", "email"])
```

## Phone call / SMS via Twilio

```python
stxn.call("Wake up! Server is down!")
stxn.sms("Build finished successfully")
```

Requires `SCITEX_NOTIFICATION_TWILIO_*` env vars and the
`scitex-notification[twilio]` extra.

## CLI

```bash
scitex-notification send-notification "Task done!"
scitex-notification call "Wake up!" --repeat 2
scitex-notification send-sms "Build complete"
scitex-notification list-backends
scitex-notification show-config
```

## Next steps

- `03_python-api.md` — full Python surface
- `04_cli-reference.md` — full CLI surface
- `05_backends.md` — per-backend setup, env vars, availability checks
- `08_configuration.md` — YAML config and level-based routing
- `20_env-vars.md` — environment variables
