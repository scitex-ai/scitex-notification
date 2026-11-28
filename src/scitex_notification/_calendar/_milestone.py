#!/usr/bin/env python3
# File: src/scitex_notification/_calendar/_milestone.py

"""Account check, calendar resolution, and the verified milestone write."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Mapping, Optional

from ._client import GoogleCalendarClient
from ._credentials import load_credentials
from ._rules import (
    CalendarError,
    build_milestone_event,
    find_duplicate_milestones,
    milestone_color_id,
    parse_milestone_time,
    verify_milestone_event,
)


def verify_account(entries: list, account: str) -> None:
    """Raise unless the primary calendar (== the signed-in account) is ``account``."""
    primary = [e for e in entries if e.get("primary")]
    owner = primary[0].get("id", "") if primary else ""
    if owner.lower() != account.lower():
        raise CalendarError(
            f"the credential belongs to {owner or 'an unknown account'!r}, "
            f"not {account!r}; re-run `scitex-notification calendar authorize` "
            f"signed in as {account}"
        )


def summarize_calendar(entry: Mapping[str, Any]) -> dict:
    return {
        "name": entry.get("summaryOverride") or entry.get("summary"),
        "id": entry.get("id"),
        "access_role": entry.get("accessRole"),
        "background_color": entry.get("backgroundColor"),
        "primary": bool(entry.get("primary")),
        "description": entry.get("description") or "",
    }


def resolve_calendar(entries: list, name: str) -> dict:
    """The one writable calendar called exactly ``name``."""
    matches = [
        e for e in entries if name in (e.get("summaryOverride"), e.get("summary"))
    ]
    if not matches:
        names = sorted(str(summarize_calendar(e)["name"]) for e in entries)
        raise CalendarError(f"no calendar named {name!r}; visible: {names}")
    if len(matches) > 1:
        raise CalendarError(f"{len(matches)} calendars are named {name!r}; ambiguous")
    entry = matches[0]
    if entry.get("accessRole") not in ("owner", "writer"):
        raise CalendarError(
            f"calendar {name!r} is {entry.get('accessRole')!r} for this account; "
            "it needs write access"
        )
    return entry


def list_calendars(client: Optional[GoogleCalendarClient] = None) -> dict:
    """Account-verified list of the calendars the configured account sees."""
    client = client or GoogleCalendarClient(load_credentials())
    entries = client.calendar_list()
    verify_account(entries, client.credentials.account)
    return {
        "account": client.credentials.account,
        "calendars": [summarize_calendar(e) for e in entries],
    }


def add_milestone(
    calendar: str,
    title: str,
    at: Any,
    note: Optional[str] = None,
    *,
    dry_run: bool = False,
    color_id: Optional[str] = None,
    client: Optional[GoogleCalendarClient] = None,
) -> dict:
    """Record one milestone; return what happened.

    ``status`` is ``created`` (written, read back and verified), ``exists``
    (an entry with this title at this second is already there; nothing
    written) or ``dry_run`` (every check done read-only; ``would_create``
    is True). Any failed check raises :class:`CalendarError`. ``color_id``
    overrides the colour rule.
    """
    when = parse_milestone_time(at)
    build_milestone_event(title, when, note)  # validate before any network
    client = client or GoogleCalendarClient(load_credentials())
    entries = client.calendar_list()
    verify_account(entries, client.credentials.account)
    entry = resolve_calendar(entries, calendar)
    chosen = (
        color_id
        if color_id is not None
        else milestone_color_id(entry.get("backgroundColor"))
    )
    event = build_milestone_event(title, when, note, color_id=chosen)
    result = {
        "account": client.credentials.account,
        "calendar": summarize_calendar(entry)["name"],
        "calendar_id": entry["id"],
        "title": event["summary"],
        "at": when.isoformat(),
        "color_id": chosen,
    }
    window = _dt.timedelta(seconds=1)
    nearby = client.events_between(entry["id"], when - window, when + window)
    existing = find_duplicate_milestones(nearby, title, when)
    if existing:
        return {
            **result,
            "status": "exists",
            "event_id": existing[0].get("id"),
            "html_link": existing[0].get("htmlLink"),
        }
    if dry_run:
        return {**result, "status": "dry_run", "would_create": True, "event": event}
    created = client.insert_event(entry["id"], event)
    saved = client.get_event(entry["id"], created["id"])
    problems = verify_milestone_event(saved, event)
    if problems:
        raise CalendarError(
            f"saved event {created['id']} breaks the milestone rules: "
            + "; ".join(problems)
        )
    return {
        **result,
        "status": "created",
        "event_id": saved.get("id"),
        "html_link": saved.get("htmlLink"),
        "start": saved["start"].get("dateTime"),
        "end": saved["end"].get("dateTime"),
        "verified": True,
    }


# EOF
