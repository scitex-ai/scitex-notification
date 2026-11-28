#!/usr/bin/env python3
# File: src/scitex_notification/_calendar/_rules.py

"""Pure milestone rules: time, event body, duplicates, verification."""

from __future__ import annotations

import datetime as _dt
import re
from typing import Any, Mapping, Optional
from zoneinfo import ZoneInfo

TIMEZONE = "Asia/Tokyo"
SCITEX_NAVY = "#1e293b"
MILESTONE_COLOR_ID = "9"
# The two narrowest scopes that do the job: read the calendar list (verify
# the account, find calendars) and read/write events.
SCOPES = (
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events",
)
_MAX_TITLE = 200


class CalendarError(RuntimeError):
    """A calendar operation cannot be done as asked (never a silent skip)."""


class CalendarInputError(CalendarError, ValueError):
    """The requested milestone itself is invalid (time, title, colour)."""


def parse_milestone_time(at: Any) -> _dt.datetime:
    """Return ``at`` as an aware Asia/Tokyo datetime, whole seconds.

    ``at`` is an aware :class:`datetime.datetime` or an ISO 8601 string with
    an offset or ``Z``. A naive time is rejected: a milestone's time must be
    unambiguous, so the caller states its zone.
    """
    if isinstance(at, str):
        text = at.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            value = _dt.datetime.fromisoformat(text)
        except ValueError:
            raise CalendarInputError(f"time {at!r} is not an ISO 8601 date-time")
    elif isinstance(at, _dt.datetime):
        value = at
    else:
        raise CalendarInputError("time must be an ISO 8601 string or a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CalendarInputError(
            f"time {at!r} has no UTC offset; give one (+09:00 or Z)"
        )
    return value.astimezone(ZoneInfo(TIMEZONE)).replace(microsecond=0)


def check_title(title: str) -> str:
    """The stripped title, or :class:`CalendarError` if it is not one line."""
    if not isinstance(title, str) or not title.strip():
        raise CalendarInputError("title must be non-empty")
    if "\n" in title or "\r" in title:
        raise CalendarInputError("title must be a single line")
    if len(title) > _MAX_TITLE:
        raise CalendarInputError(f"title is longer than {_MAX_TITLE} characters")
    return title.strip()


def milestone_color_id(calendar_background: Optional[str]) -> Optional[str]:
    """``None`` (use the calendar colour) for SciTeX navy, else id ``"9"``."""
    if (calendar_background or "").strip().lower() == SCITEX_NAVY:
        return None
    return MILESTONE_COLOR_ID


def build_milestone_event(
    title: str,
    at: Any,
    note: Optional[str] = None,
    *,
    color_id: Optional[str] = None,
) -> dict:
    """The Calendar API event body for one milestone (no network)."""
    when = parse_milestone_time(at)
    stamp = {"dateTime": when.isoformat(), "timeZone": TIMEZONE}
    event: dict = {
        "summary": check_title(title),
        "start": dict(stamp),
        "end": dict(stamp),
        "transparency": "transparent",
        "visibility": "private",
        "reminders": {"useDefault": False, "overrides": []},
    }
    if note is not None and note.strip():
        event["description"] = note.strip()
    if color_id is not None:
        if not re.fullmatch(r"[1-9]|1[01]", str(color_id)):
            raise CalendarInputError("color id must be one of Google's event ids 1-11")
        event["colorId"] = str(color_id)
    return event


def event_time(stamp: Optional[Mapping[str, Any]]) -> Optional[_dt.datetime]:
    """The aware Asia/Tokyo time of an API ``start``/``end`` (None: all-day)."""
    text = (stamp or {}).get("dateTime")
    return parse_milestone_time(text) if text else None


def find_duplicate_milestones(events: list, title: str, at: Any) -> list:
    """Events among ``events`` with the same title starting at the same second."""
    want_title, want_at = check_title(title), parse_milestone_time(at)
    return [
        e
        for e in events
        if e.get("status") != "cancelled"
        and (e.get("summary") or "").strip() == want_title
        and event_time(e.get("start")) == want_at
    ]


def verify_milestone_event(
    saved: Mapping[str, Any], expected: Mapping[str, Any]
) -> list:
    """Every way ``saved`` breaks the milestone rules (empty list = all good)."""
    problems = []
    start, end = event_time(saved.get("start")), event_time(saved.get("end"))
    want = event_time(expected["start"])
    if start != want:
        problems.append(f"start is {start}, expected {want}")
    if end != start:
        problems.append(f"duration is not zero (start {start}, end {end})")
    if saved.get("summary") != expected["summary"]:
        problems.append("title differs from the requested title")
    if saved.get("transparency") != "transparent":
        problems.append("not marked Free (transparency is not 'transparent')")
    if saved.get("visibility") != "private":
        problems.append("not Private")
    reminders = saved.get("reminders") or {}
    if reminders.get("useDefault") is not False or reminders.get("overrides"):
        problems.append("reminders are not off")
    if saved.get("colorId") != expected.get("colorId"):
        problems.append(
            f"colour id is {saved.get('colorId')!r}, "
            f"expected {expected.get('colorId')!r}"
        )
    return problems


# EOF
