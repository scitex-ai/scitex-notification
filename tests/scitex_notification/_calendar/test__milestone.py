"""Account check and calendar resolution on real calendarList entries."""

import pytest

from scitex_notification import CalendarError
from scitex_notification._calendar._milestone import resolve_calendar, verify_account

ENTRIES = [
    {
        "id": "dev@example.org",
        "summary": "dev@example.org",
        "primary": True,
        "accessRole": "owner",
    },
    {
        "id": "eco@group",
        "summary": "SciTeX Ecosystem",
        "accessRole": "writer",
        "backgroundColor": "#1e293b",
    },
    {"id": "ro@group", "summary": "Holidays", "accessRole": "reader"},
    {"id": "a@group", "summary": "Twin", "accessRole": "owner"},
    {"id": "b@group", "summary": "Twin", "accessRole": "owner"},
]


def test_matching_primary_account_passes():
    # Arrange
    account = "DEV@example.org"
    # Act
    outcome = verify_account(ENTRIES, account)
    # Assert
    assert outcome is None


def test_other_account_is_refused():
    # Arrange
    account = "ops@example.org"
    # Act
    call = lambda: verify_account(ENTRIES, account)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="belongs to 'dev@example.org'"):
        call()


def test_calendar_is_found_by_exact_name():
    # Arrange
    name = "SciTeX Ecosystem"
    # Act
    entry = resolve_calendar(ENTRIES, name)
    # Assert
    assert entry["id"] == "eco@group"


def test_unknown_calendar_lists_what_is_visible():
    # Arrange
    name = "SciTeX Eco"
    # Act
    call = lambda: resolve_calendar(ENTRIES, name)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="visible:"):
        call()


def test_read_only_calendar_is_refused():
    # Arrange
    name = "Holidays"
    # Act
    call = lambda: resolve_calendar(ENTRIES, name)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="needs write access"):
        call()


def test_ambiguous_calendar_name_is_refused():
    # Arrange
    name = "Twin"
    # Act
    call = lambda: resolve_calendar(ENTRIES, name)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="ambiguous"):
        call()
