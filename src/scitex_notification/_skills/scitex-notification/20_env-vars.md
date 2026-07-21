---
description: |
  [TOPIC] scitex-notification Environment Variables
  [DETAILS] SCITEX_NOTIFICATION_* env vars — default backend, env-file source, Twilio credentials, SMTP credentials, webhook URL, Telegram token.
tags: [scitex-notification-env-vars]
---

# Environment Variables

Read at import time and on demand by `scitex_notification`.

## Core routing

| Variable                                 | Purpose                                        |
|------------------------------------------|------------------------------------------------|
| `SCITEX_NOTIFICATION_DEFAULT_BACKEND`    | Default single backend (e.g. `audio`, `email`) |
| `SCITEX_NOTIFICATION_ENV_SRC`            | Path to a `.env` file auto-loaded on import    |
| `SCITEX_NOTIFICATION_CONFIG`             | Path to a YAML config file                     |

## Twilio (phone + SMS)

| Variable                              | Purpose                                  |
|---------------------------------------|------------------------------------------|
| `SCITEX_NOTIFICATION_TWILIO_SID`      | Twilio Account SID                       |
| `SCITEX_NOTIFICATION_TWILIO_TOKEN`    | Twilio Auth Token                        |
| `SCITEX_NOTIFICATION_TWILIO_FROM`     | Sending phone number (E.164)             |
| `SCITEX_NOTIFICATION_TWILIO_TO`       | Default destination number               |

## SMTP (email)

| Variable                              | Purpose                          |
|---------------------------------------|----------------------------------|
| `SCITEX_NOTIFICATION_SMTP_HOST`       | SMTP server hostname             |
| `SCITEX_NOTIFICATION_SMTP_PORT`       | SMTP server port                 |
| `SCITEX_NOTIFICATION_SMTP_USER`       | SMTP user                        |
| `SCITEX_NOTIFICATION_SMTP_PASSWORD`   | SMTP password                    |
| `SCITEX_NOTIFICATION_SMTP_FROM`       | Default `From:` address          |
| `SCITEX_NOTIFICATION_SMTP_TO`         | Default `To:` address            |

## Webhook / Telegram

| Variable                                | Purpose                          |
|-----------------------------------------|----------------------------------|
| `SCITEX_NOTIFICATION_WEBHOOK_URL`       | HTTP POST destination            |
| `SCITEX_NOTIFICATION_TELEGRAM_TOKEN`    | Telegram bot token               |
| `SCITEX_NOTIFICATION_TELEGRAM_CHAT_ID`  | Telegram chat ID                 |

## Precedence

```
1. Explicit kwargs to alert / call / sms
2. ./config.yaml (project-local)
3. $SCITEX_NOTIFICATION_CONFIG file
4. ~/.scitex/notification/config.yaml
5. Environment variables above
6. Built-in defaults
```

See `08_configuration.md` for the YAML schema and `05_backends.md` for
per-backend availability checks.
