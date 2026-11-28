"""Milestone rules: time, event body, duplicates, verification (pure, no mocks)."""

import pytest

from scitex_notification import CalendarInputError, build_milestone_event
from scitex_notification._calendar._rules import (
    find_duplicate_milestones,
    milestone_color_id,
    parse_milestone_time,
    verify_milestone_event,
)

AT = "2026-11-28T09:24:40.734328Z"
JST = "2026-11-28T18:24:40+09:00"
STAMP = {"dateTime": JST, "timeZone": "Asia/Tokyo"}


# -- time ---------------------------------------------------------------


def test_utc_time_is_shown_in_tokyo_whole_seconds():
    # Arrange
    at = AT
    # Act
    when = parse_milestone_time(at)
    # Assert
    assert when.isoformat() == JST


def test_naive_time_is_rejected():
    # Arrange
    at = "2026-11-28T09:24:40"
    # Act
    call = lambda: parse_milestone_time(at)  # noqa: E731
    # Assert
    with pytest.raises(CalendarInputError, match="no UTC offset"):
        call()


def test_garbage_time_is_rejected():
    # Arrange
    at = "yesterday"
    # Act
    call = lambda: parse_milestone_time(at)  # noqa: E731
    # Assert
    with pytest.raises(CalendarInputError, match="ISO 8601"):
        call()


# -- event body ---------------------------------------------------------


@pytest.fixture
def event():
    return build_milestone_event("【clew】| DONE | v0.38.0", AT, "Done. https://x.org/")


def test_event_start_is_the_milestone_time(event):
    # Arrange
    expected = STAMP
    # Act
    start = event["start"]
    # Assert
    assert start == expected


def test_event_has_zero_duration(event):
    # Arrange
    start = event["start"]
    # Act
    end = event["end"]
    # Assert
    assert end == start


def test_event_is_free(event):
    # Arrange
    key = "transparency"
    # Act
    value = event[key]
    # Assert
    assert value == "transparent"


def test_event_is_private(event):
    # Arrange
    key = "visibility"
    # Act
    value = event[key]
    # Assert
    assert value == "private"


def test_event_has_reminders_off(event):
    # Arrange
    key = "reminders"
    # Act
    value = event[key]
    # Assert
    assert value == {"useDefault": False, "overrides": []}


def test_event_carries_the_note(event):
    # Arrange
    key = "description"
    # Act
    value = event[key]
    # Assert
    assert value == "Done. https://x.org/"


def test_event_uses_calendar_colour_unless_asked(event):
    # Arrange
    key = "colorId"
    # Act
    present = key in event
    # Assert
    assert present is False


@pytest.mark.parametrize("title", ["", "  ", "two\nlines", "x" * 201])
def test_bad_titles_are_rejected(title):
    # Arrange
    at = AT
    # Act
    call = lambda: build_milestone_event(title, at)  # noqa: E731
    # Assert
    with pytest.raises(CalendarInputError):
        call()


def test_color_id_must_be_a_google_event_id():
    # Arrange
    bad = "12"
    # Act
    call = lambda: build_milestone_event("t", AT, color_id=bad)  # noqa: E731
    # Assert
    with pytest.raises(CalendarInputError, match="color id"):
        call()


def test_navy_calendar_keeps_its_colour_other_calendars_get_blue_9():
    # Arrange
    navy, other = "#1E293B", "#9fe1e7"
    # Act
    chosen = (milestone_color_id(navy), milestone_color_id(other))
    # Assert
    assert chosen == (None, "9")


# -- duplicates and verification ----------------------------------------


def _event(summary, start, **extra):
    return {
        "summary": summary,
        "start": {"dateTime": start},
        "end": {"dateTime": start},
        **extra,
    }


def test_duplicate_means_same_title_at_same_second():
    # Arrange
    events = [
        _event("A", "2026-11-28T18:24:40+09:00", id="same"),
        _event("A", "2026-11-28T18:24:41+09:00", id="next-second"),
        _event("B", "2026-11-28T18:24:40+09:00", id="other-title"),
        _event("A", "2026-11-28T18:24:40+09:00", id="gone", status="cancelled"),
    ]
    # Act
    found = find_duplicate_milestones(events, "A", AT)
    # Assert
    assert [e["id"] for e in found] == ["same"]


def test_verify_accepts_a_correct_saved_event():
    # Arrange
    expected = build_milestone_event("A", AT, color_id="9")
    saved = {**expected, "id": "e1"}
    # Act
    problems = verify_milestone_event(saved, expected)
    # Assert
    assert problems == []


@pytest.mark.parametrize(
    "change, word",
    [
        ({"end": {"dateTime": "2026-11-28T18:54:40+09:00"}}, "duration"),
        ({"transparency": "opaque"}, "Free"),
        ({"visibility": "default"}, "Private"),
        ({"reminders": {"useDefault": True}}, "reminders"),
        ({"colorId": "5"}, "colour"),
    ],
)
def test_verify_names_the_broken_rule(change, word):
    # Arrange
    expected = build_milestone_event("A", AT, color_id="9")
    saved = {**expected, **change}
    # Act
    problems = " | ".join(verify_milestone_event(saved, expected))
    # Assert
    assert word in problems
