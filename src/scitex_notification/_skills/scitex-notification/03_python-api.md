---
description: |
  [TOPIC] scitex-notification Python API
  [DETAILS] Top-level public callables — alert, alert_async, call, call_async, sms, sms_async, available_backends.
tags: [scitex-notification-python-api]
---

# Python API

Top-level public surface re-exported from `scitex_notification`.

## Alert

| Name                  | Purpose                                                |
|-----------------------|--------------------------------------------------------|
| `alert(msg, ...)`     | Send a notification (sync; spawns thread for async I/O)|
| `alert_async(msg, ...)` | Async version                                        |

Common kwargs: `backend=str | list[str] | None`, `level="info"|"warning"|"error"|"critical"`, `fallback=bool`.

## Twilio (phone / SMS)

| Name              | Purpose                                                  |
|-------------------|----------------------------------------------------------|
| `call(msg, ...)`  | Make a phone call (sync)                                 |
| `call_async(...)` | Async version                                            |
| `sms(msg, ...)`   | Send an SMS (sync)                                       |
| `sms_async(...)`  | Async version                                            |

Requires `SCITEX_NOTIFICATION_TWILIO_*` env vars (see `20_env-vars.md`).

## Introspection

| Name                    | Purpose                                          |
|-------------------------|--------------------------------------------------|
| `available_backends()`  | List of backend names whose deps + creds are OK  |
| `__version__`           | Installed package version                        |

## Example

```python
import scitex_notification as stxn

print(stxn.available_backends())            # ['audio', 'email', ...]

stxn.alert("Done")                          # default fallback
stxn.alert("Err", backend="email", level="error")
stxn.alert("Critical", backend=["audio", "email"])

# Async
import asyncio
asyncio.run(stxn.alert_async("Hi"))
```

## Beyond the top level

- `06_python-api.md` — extended reference
- `07_mcp-tools.md` — MCP tools that wrap these calls
- `08_configuration.md` — YAML config and level-based routing
