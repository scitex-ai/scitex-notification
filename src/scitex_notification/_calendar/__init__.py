#!/usr/bin/env python3
# File: src/scitex_notification/_calendar/__init__.py

"""Milestone entries in Google Calendar, written through the Calendar API.

A *milestone* is a point in time: something was published, merged or
verified. It is recorded as one event with

- start == end (zero duration) at the actual time, shown in Asia/Tokyo,
- ``transparency = "transparent"`` (Free) and ``visibility = "private"``,
- reminders off (``useDefault = false``, no overrides),
- the calendar's own colour when that is the SciTeX navy ``#1E293B``,
  otherwise Google's closest event blue, colour id ``9``,
- a short title and a Markdown note (outcome + source link).

Before writing, :func:`add_milestone` checks that the credential belongs to
the configured account, resolves the calendar by its exact name, and looks
for an existing entry with the same title at the same second. A duplicate
is reported, never written twice. After writing, the saved event is read
back and every rule above is checked; a mismatch raises.

Modules: ``_rules`` (pure event rules), ``_credentials`` (where the OAuth
client and token live), ``_client`` (stdlib HTTP client), ``_milestone``
(account/calendar resolution and the write), ``_authorize`` (one-time owner
consent).
"""

from ._authorize import authorize_calendar, build_authorization_url
from ._client import GoogleCalendarClient
from ._credentials import CalendarCredentials, load_credentials
from ._milestone import add_milestone, list_calendars
from ._rules import (
    MILESTONE_COLOR_ID,
    SCITEX_NAVY,
    SCOPES,
    TIMEZONE,
    CalendarError,
    CalendarInputError,
    build_milestone_event,
    find_duplicate_milestones,
    milestone_color_id,
    parse_milestone_time,
    verify_milestone_event,
)

__all__ = [
    "CalendarCredentials",
    "CalendarError",
    "CalendarInputError",
    "GoogleCalendarClient",
    "MILESTONE_COLOR_ID",
    "SCITEX_NAVY",
    "SCOPES",
    "TIMEZONE",
    "add_milestone",
    "authorize_calendar",
    "build_authorization_url",
    "build_milestone_event",
    "find_duplicate_milestones",
    "list_calendars",
    "load_credentials",
    "milestone_color_id",
    "parse_milestone_time",
    "verify_milestone_event",
]

# EOF
