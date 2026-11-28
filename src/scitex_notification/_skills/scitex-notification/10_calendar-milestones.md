---
description: |
  [TOPIC] Record milestones (published, merged, verified) as zero-duration, Free, Private Google Calendar entries.
  [DETAILS] add_milestone / list_calendars / authorize_calendar / build_milestone_event / CalendarError / CalendarInputError; CLI `calendar authorize`, `calendar list-calendars`, `calendar add-milestone`; env SCITEX_NOTIFICATION_GCAL_ACCOUNT / _CLIENT_FILE / _TOKEN_FILE.
tags: [scitex-notification-calendar-milestones]
---

# Calendar milestones

A milestone is a point in time: a release was published, a PR merged, a
result verified. `add_milestone` writes it as one Google Calendar event and
enforces the rules, so a caller cannot get them wrong:

| Rule | How |
|---|---|
| Zero duration | `start == end` at the given second, shown in Asia/Tokyo |
| Free | `transparency = "transparent"` |
| Private | `visibility = "private"` |
| Reminders off | `reminders = {useDefault: false, overrides: []}` |
| Colour | calendar default when it is SciTeX navy `#1E293B`, else event colour id `9` |
| Right account | the token's primary calendar must equal `SCITEX_NOTIFICATION_GCAL_ACCOUNT` |
| Right calendar | exact name, exactly one match, writer/owner access |
| No duplicates | same title at the same second in that calendar -> `status: "exists"`, nothing written |
| Saved as asked | the new event is read back; any broken rule raises `CalendarError` |

The time must carry an offset (`Z`, `+09:00`); a naive time is rejected.
Use the authoritative time: registry upload time for a publication, PR merge
time for a merge, the run record for a verification.

## CLI

```bash
# what the event body will be, no network
scitex-notification calendar add-milestone -c "SciTeX Ecosystem" \
    -t "【clew】| DONE | v0.38.0 published" --at 2026-11-28T09:24:40Z \
    -n "Published to PyPI. https://pypi.org/project/scitex-clew/0.38.0/" --offline

# every check (account, calendar, duplicate) read-only
scitex-notification calendar add-milestone ... --dry-run

# write it (prints status created|exists, event_id, html_link)
scitex-notification calendar add-milestone ...

scitex-notification calendar list-calendars   # names, ids, colours, descriptions
```

Exit codes: 0 ok, 1 credential/account/API failure, 2 invalid milestone.

## Python

```python
import scitex_notification as stxn

stxn.add_milestone(
    "SciTeX R&D", "【Clew】Self-proof PASS 81/81", "2026-11-28T07:49:01Z",
    note="PASS on clew 0.37.3. https://github.com/org/repo/pull/308",
    dry_run=True,
)
```

## One-time setup (account owner)

1. In Google Cloud (a project of the account's organisation), enable the
   **Google Calendar API**, configure the OAuth consent screen (Internal for
   a Workspace domain), and create an OAuth client of type **Desktop app**.
   Download its JSON.
2. Save it as `$SCITEX_DIR/notification/secrets/gcal-client.json`
   (or point `SCITEX_NOTIFICATION_GCAL_CLIENT_FILE` at it) and `chmod 600` it.
3. `export SCITEX_NOTIFICATION_GCAL_ACCOUNT=<account email>`.
4. `scitex-notification calendar authorize` and open the printed URL in a
   browser signed in as that account. The browser must reach
   `127.0.0.1:8765` on the host running the command; from another machine
   use `ssh -L 8765:127.0.0.1:8765 <host>`. Allow both permissions.
   The refresh token is stored (0600) in `gcal-token.json` only after the
   calendar list proves it belongs to the configured account.

Scopes are the two narrowest that work: `calendar.calendarlist.readonly`
and `calendar.events`. No secret is printed or returned.

For a non-Workspace account use an **External** app and add the account
as a **Test user** (otherwise consent fails with `403 access_denied`).
In Testing status Google expires the refresh token after ~7 days: writes
then fail with `invalid_grant`; re-run `calendar authorize`, or publish the
app to stop the expiry. Full guide with both SSH tunnel options and a
troubleshooting table: `docs/sphinx/calendar_setup.rst`
(https://scitex-notification.readthedocs.io/en/latest/calendar_setup.html).
