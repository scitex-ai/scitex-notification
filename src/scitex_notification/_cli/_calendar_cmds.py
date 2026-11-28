#!/usr/bin/env python3
# File: src/scitex_notification/_cli/_calendar_cmds.py

"""CLI: Google Calendar milestones (``scitex-notification calendar ...``).

Every leaf prints one JSON object. Exit codes: 0 ok, 1 calendar failure
(credential, account, API), 2 invalid input.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


def _emit(payload: dict) -> None:
    click.echo(json.dumps(payload, ensure_ascii=False))


def _fail(exc: Exception, code: int) -> None:
    click.echo(f"error: {exc}", err=True)
    sys.exit(code)


def _read_note(note, note_file):
    if note and note_file:
        _fail(ValueError("pass either --note or --note-file, not both"), 2)
    if note_file:
        return Path(note_file).read_text(encoding="utf-8")
    return note


@click.group("calendar")
def calendar_group():
    """Record milestones in Google Calendar (zero duration, Free, Private).

    \b
    Configure SCITEX_NOTIFICATION_GCAL_ACCOUNT (and optionally
    SCITEX_NOTIFICATION_GCAL_CLIENT_FILE / _TOKEN_FILE), then run
    `calendar authorize` once as the account owner.

    Setup guide (Google Cloud client, SSH tunnel, 7-day Testing expiry):
    https://scitex-notification.readthedocs.io/en/latest/calendar_setup.html
    """


@calendar_group.command("authorize")
@click.option("--port", type=int, default=8765, show_default=True)
@click.option("--timeout", "timeout_s", type=float, default=600.0, show_default=True)
@click.option("--dry-run", is_flag=True, help="Check the client file; no consent.")
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Suppress interactive confirmation (none is asked).",
)
def authorize_cmd(port, timeout_s, dry_run, yes):
    """Owner step: grant calendar access once and store the token (0600).

    Open the printed URL in a browser signed in as the configured account.
    The browser must reach 127.0.0.1:PORT on this host (or use ssh -L).

    \b
    Example:
      $ scitex-notification calendar authorize --port 8765
    """
    from scitex_notification import CalendarError, authorize_calendar, load_credentials

    try:
        if dry_run:
            creds = load_credentials(require_token=False)
            _emit({**creds.describe(), "status": "dry_run"})
            return
        result = authorize_calendar(
            lambda url: click.echo(
                f"Open this URL signed in as the account:\n{url}", err=True
            ),
            port=port,
            timeout_s=timeout_s,
        )
    except CalendarError as exc:
        _fail(exc, 1)
    _emit(result)


@calendar_group.command("list-calendars")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON (default).")
def list_calendars_cmd(as_json):
    """List calendars the configured account sees, after verifying the account.

    \b
    Example:
      $ scitex-notification calendar list-calendars
    """
    from scitex_notification import CalendarError, list_calendars

    try:
        _emit(list_calendars())
    except CalendarError as exc:
        _fail(exc, 1)


@calendar_group.command("add-milestone")
@click.option("--calendar", "-c", required=True, help="Exact calendar name.")
@click.option("--title", "-t", required=True, help="Short single-line title.")
@click.option("--at", "at", required=True, help="ISO 8601 time with offset or Z.")
@click.option("--note", "-n", help="Markdown note: outcome + source link.")
@click.option("--note-file", type=click.Path(exists=True, dir_okay=False))
@click.option("--color-id", help="Override the colour rule (Google event id 1-11).")
@click.option("--offline", is_flag=True, help="Print the event body; no network.")
@click.option("--dry-run", is_flag=True, help="All checks read-only; write nothing.")
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Suppress interactive confirmation (none is asked).",
)
def add_milestone_cmd(
    calendar, title, at, note, note_file, color_id, offline, dry_run, yes
):
    """Record one milestone: zero duration, Free, Private, reminders off.

    An entry with the same title at the same second in that calendar is
    reported (status "exists") and not written again. A new entry is read
    back and verified.

    \b
    Examples:
      $ scitex-notification calendar add-milestone -c "SciTeX Ecosystem" \\
          -t "【clew】| DONE | v0.38.0 published" --at 2026-11-28T09:24:40Z \\
          -n "Published to PyPI. https://pypi.org/project/scitex-clew/0.38.0/"
      $ scitex-notification calendar add-milestone -c X -t T --at 2026-01-01T00:00Z --offline
    """
    from scitex_notification import (
        CalendarError,
        CalendarInputError,
        add_milestone,
        build_milestone_event,
    )

    text = _read_note(note, note_file)
    try:
        if offline:
            event = build_milestone_event(title, at, text, color_id=color_id)
            _emit({"status": "offline", "calendar": calendar, "event": event})
            return
        result = add_milestone(
            calendar, title, at, text, dry_run=dry_run, color_id=color_id
        )
    except CalendarInputError as exc:
        _fail(exc, 2)
    except CalendarError as exc:
        _fail(exc, 1)
    _emit(result)


COMMANDS = [calendar_group]

# EOF
