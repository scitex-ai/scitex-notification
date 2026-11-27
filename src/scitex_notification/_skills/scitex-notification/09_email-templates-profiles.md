---
description: |
  [TOPIC] Email message templates (built-in `notice`), env-configured sender/recipient profiles, and per-key repeat suppression.
  [DETAILS] render_template / validate_message / register_template / MessageFormatError; get_profile / send_with_profile; RateLimiter; send_email(from_name=); CLI render-message, validate-message, send-email, show-profile, list-templates; MCP notification_render_message / notification_validate_message.
tags: [scitex-notification-email-templates-profiles]
---

# Email templates, profiles and repeat suppression

Three independent pieces that compose in `send_with_profile`:

| Piece | What it fixes |
|---|---|
| **Template** (`notice`) | Every notice has the same shape, so a person sees in one glance whether to act. Checked before sending; a bad message never leaves. |
| **Profile** | A role name ("ops", "operator") resolves to one coherent sender, display name, recipient, SMTP server and credential. The package hardcodes no address. |
| **RateLimiter** | The same alarm is not mailed again within a window (file state + `flock`, safe across processes). |

## The `notice` template

```text
Subject: [SciTeX][<agent>] <KIND>: <one line>          KIND: NEEDS-YOU | DONE | STOPPED | FYI

NEEDS YOU
1. <question, one line>
   A) <option>  B) <option>  -> recommend: A
   reply: "1 A"
DONE
- <outcome, one line, with link>
RUNNING (no action needed)
- <item>
--
agent: <name> | host: <host> | card/PR: <ids>
```

Rules the validator enforces (all violations are reported at once, as `MessageFormatError.violations`):

- subject is `[SciTeX][<agent>] <KIND>: <title>` on one line, KIND from the list;
- the first body line is a section header; headers are exactly the three above, in that order, each at most once; empty sections are omitted;
- NEEDS YOU holds numbered questions (1, 2, ...), each with an options line ending `-> recommend: X` (X one of its options) and a `reply: "N X"` line; a NEEDS-YOU subject needs at least one; a NEEDS YOU section needs a NEEDS-YOU subject;
- DONE / RUNNING items are single `- ` lines;
- footer: `--` then `agent: <name> | host: <host> | card/PR: <ids>`, agent matching the subject (and `agent=` when given);
- at most `NOTICE_MAX_LINES` (20) non-empty lines, each at most `NOTICE_MAX_LINE_CHARS` (200);
- no credential-shaped text (private keys, GitHub/OpenAI/Slack/AWS tokens, `password=...`). Best effort, not a secret scanner.

Render from data instead of writing it by hand:

```python
import scitex_notification as stxn

subject, body = stxn.render_template("notice", {
    "kind": "NEEDS-YOU",
    "title": "archive quota",
    "questions": [{"text": "Raise the quota to 2 TB?",
                   "options": ["yes", "no, prune old runs"],
                   "recommend": "A"}],          # a letter or the option text
    "done": ["nightly backup verified https://example.org/run/42"],
    "running": ["re-index of the archive"],
    "meta": {"agent": "worker-1", "host": "compute-01", "refs": ["card-7", "#12"]},
})
stxn.validate_message("notice", subject, body, agent="worker-1")  # hand-written text too
data = stxn.load_message_data("notice.yaml")                     # dict, .json or .yaml
```

Your own template: `register_template(name, render, validate, replace=False)` where `render(data) -> (subject, body)` and `validate(subject, body, **context)` raises `MessageFormatError`. `render_template` always runs the validator on what it rendered. `list_templates()` lists names.

## Profiles

Configured only through the environment (`<NAME>` = profile name upper-cased, `-` -> `_`):

| Variable | |
|---|---|
| `SCITEX_NOTIFICATION_PROFILE_<NAME>_FROM` | sender address (required) |
| `SCITEX_NOTIFICATION_PROFILE_<NAME>_FROM_NAME` | display name in the From header (optional) |
| `SCITEX_NOTIFICATION_PROFILE_<NAME>_TO` | one recipient address (required) |
| `SCITEX_NOTIFICATION_PROFILE_<NAME>_SMTP_HOST` | SMTP host (required) |
| `SCITEX_NOTIFICATION_PROFILE_<NAME>_SMTP_PORT` | default 587 (STARTTLS) |
| `SCITEX_NOTIFICATION_PROFILE_<NAME>_PASSWORD` | SMTP password, or |
| `SCITEX_NOTIFICATION_PROFILE_<NAME>_PASSWORD_FILE` | a file holding it; must be a regular file you own with mode 0600 (no group/other bits) |

A profile never falls back to the generic `SCITEX_NOTIFICATION_EMAIL_*` chain, so it cannot pair its sender with another identity's password. Login and envelope sender are the bare `FROM` address; `FROM_NAME` only changes the header.

Example roles (values are deployment config, not package defaults):

```bash
# ops: machine alarms to the dev list
export SCITEX_NOTIFICATION_PROFILE_OPS_FROM=no-reply@example.org
export SCITEX_NOTIFICATION_PROFILE_OPS_TO=dev@example.org
export SCITEX_NOTIFICATION_PROFILE_OPS_SMTP_HOST=smtp.example.org
export SCITEX_NOTIFICATION_PROFILE_OPS_PASSWORD_FILE=~/.config/scitex/no-reply.pw

# operator: agent notices to the human operator, with a display name
export SCITEX_NOTIFICATION_PROFILE_OPERATOR_FROM=agent@example.org
export SCITEX_NOTIFICATION_PROFILE_OPERATOR_FROM_NAME="SciTeX Agent (worker-1)"
export SCITEX_NOTIFICATION_PROFILE_OPERATOR_TO=operator@example.org
export SCITEX_NOTIFICATION_PROFILE_OPERATOR_SMTP_HOST=smtp.example.org
export SCITEX_NOTIFICATION_PROFILE_OPERATOR_PASSWORD_FILE=~/.config/scitex/agent.pw
```

```python
stxn.get_profile("ops").describe()          # dict without the password
stxn.send_with_profile(
    "ops", "disk 91% on /data", body,
    dedupe_key="disk:/data", dedupe_window_s=3600,   # at most one mail per hour per key
    template=None,                                   # or "notice" to validate first
    message_id=None, dry_run=False,
)  # -> {"status": "sent" | "suppressed" | "dry_run", "from", "to", ...}
```

Order inside `send_with_profile`: template validation, then the dedupe check, then SMTP. A failed send is not recorded, so its retry is not suppressed. `dry_run=True` validates and peeks at the limiter without recording or connecting (`would_send` in the result). SMTP errors propagate.

## Repeat suppression on its own

```python
limiter = stxn.RateLimiter(window_s=3600, state_dir=None, max_events=1)
if limiter.allow("disk:/data"):          # check + record, atomic across processes
    ...
limiter.peek("disk:/data")               # check only
with limiter.hold("disk:/data") as ok:   # record only if the block succeeds
    if ok: send()
limiter.suppressed_count("disk:/data")
```

State: `$SCITEX_NOTIFICATION_RATE_LIMIT_DIR`, else `$SCITEX_DIR/notification/runtime/rate-limit` (`~/.scitex` by default); one 0600 JSON file per hashed key.

## Display name on plain `send_email`

`send_email(to, subject, body, *, from_addr=, from_name=None, ...)` sets `From: "<from_name>" <from_addr>` (RFC 2047 encoded when non-ASCII; CR/LF rejected). SMTP login and envelope sender stay `from_addr`. STARTTLS verifies the server certificate (system CA store, host name checked); pass `ssl_context=ssl.create_default_context(cafile=...)` for a private CA. Feature-detect with `"from_name" in inspect.signature(stxn.send_email).parameters`.

## CLI

```bash
scitex-notification list-templates
scitex-notification render-message notice.json              # prints {"subject", "body"}
scitex-notification validate-message -s "$SUBJECT" -f body.txt --agent worker-1   # exit 2 + violations
scitex-notification show-profile ops                        # no password
scitex-notification send-email -p ops -s "disk 91% on /data" -f alarm.txt \
    --dedupe-key disk:/data --dedupe-window 3600
scitex-notification send-email -p operator -t notice --data-file notice.json --dry-run
```

Exit codes: 0 ok, 1 SMTP failure, 2 invalid input (format violation, unknown template or profile).

## MCP

`notification_render_message(data, template="notice")` and `notification_validate_message(subject, body, template="notice", agent=None)`: render/validate only; neither sends mail.
