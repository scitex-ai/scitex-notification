#!/usr/bin/env python3
# Timestamp: "2026-05-30 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/tests/scitex_notification/test__notify_legacy.py

"""Tests for the migrated legacy notify helpers.

Covers pure helpers and explicitly synthetic SMTP transcripts:
- gen_footer() structure
- get_hostname() / get_username() return non-empty strings
- ansi_escape strips ANSI color codes
- public re-exports (notify, send_gmail) are importable

The public send_gmail body is also exercised with its explicit in-memory
SMTP factory. This checks local control flow, MIME and output, never actual
SMTP or email delivery. notify and other notification backends are not sent.
"""

from __future__ import annotations

import logging
import socket
import types

import pytest


# ---------------------------------------------------------------------------
# public re-exports
# ---------------------------------------------------------------------------
def test_notify_is_callable_public_attribute():
    """notify is exposed as a callable package attribute."""
    # Arrange
    from scitex_notification import notify

    # Act
    is_callable = callable(notify)

    # Assert
    assert is_callable


def test_send_gmail_is_callable_public_attribute():
    """send_gmail is exposed as a callable package attribute."""
    # Arrange
    from scitex_notification import send_gmail

    # Act
    is_callable = callable(send_gmail)

    # Assert
    assert is_callable


def test_notify_is_listed_in_dunder_all():
    """notify appears in scitex_notification.__all__."""
    # Arrange
    import scitex_notification as stxn

    # Act
    exported = set(stxn.__all__)

    # Assert
    assert "notify" in exported


def test_send_gmail_is_listed_in_dunder_all():
    """send_gmail appears in scitex_notification.__all__."""
    # Arrange
    import scitex_notification as stxn

    # Act
    exported = set(stxn.__all__)

    # Assert
    assert "send_gmail" in exported


# ---------------------------------------------------------------------------
# gen_footer
# ---------------------------------------------------------------------------
def test_gen_footer_embeds_sender_identifier():
    """gen_footer() embeds the sender host identifier."""
    # Arrange
    from scitex_notification._notify_legacy import gen_footer

    package = types.SimpleNamespace(__version__="9.9.9")

    # Act
    footer = gen_footer("alice@host", "run.py", package, "develop")

    # Assert
    assert "alice@host" in footer


def test_gen_footer_embeds_script_name():
    """gen_footer() embeds the originating script name."""
    # Arrange
    from scitex_notification._notify_legacy import gen_footer

    package = types.SimpleNamespace(__version__="9.9.9")

    # Act
    footer = gen_footer("alice@host", "run.py", package, "develop")

    # Assert
    assert "run.py" in footer


def test_gen_footer_embeds_package_version():
    """gen_footer() embeds the package version string."""
    # Arrange
    from scitex_notification._notify_legacy import gen_footer

    package = types.SimpleNamespace(__version__="9.9.9")

    # Act
    footer = gen_footer("alice@host", "run.py", package, "develop")

    # Assert
    assert "9.9.9" in footer


def test_gen_footer_uses_unknown_when_version_missing():
    """gen_footer() falls back to 'unknown' when package has no __version__."""
    # Arrange
    from scitex_notification._notify_legacy import gen_footer

    package = types.SimpleNamespace()

    # Act
    footer = gen_footer("u@h", "s.py", package, "main")

    # Assert
    assert "unknown" in footer


# ---------------------------------------------------------------------------
# get_hostname / get_username
# ---------------------------------------------------------------------------
def test_get_hostname_matches_socket_gethostname():
    """get_hostname() returns the system hostname from socket."""
    # Arrange
    from scitex_notification._notify_legacy import get_hostname

    # Act
    result = get_hostname()

    # Assert
    assert result == socket.gethostname()


def test_get_username_returns_nonempty_string():
    """get_username() returns a non-empty username string."""
    # Arrange
    from scitex_notification._notify_legacy import get_username

    # Act
    result = get_username()

    # Assert
    assert result != ""


# ---------------------------------------------------------------------------
# ansi_escape
# ---------------------------------------------------------------------------
def test_ansi_escape_strips_color_codes():
    """ansi_escape removes ANSI color escape sequences from text."""
    # Arrange
    from scitex_notification._notify_legacy import ansi_escape

    colored = "\x1b[31mERROR\x1b[0m done"

    # Act
    cleaned = ansi_escape.sub("", colored)

    # Assert
    assert cleaned == "ERROR done"


class SMTPTranscript:
    """Explicit in-memory SMTP collaborator; no delivery or socket operations."""

    def __init__(self, failure=None):
        self.failure = failure
        self.calls = []
        self.message = None
        self.recipients = None

    def _record(self, name, *args):
        self.calls.append((name, *args))
        if self.failure == name:
            raise RuntimeError(f"synthetic {name} refusal")

    def __call__(self, host, port):
        self._record("construct", host, port)
        return self

    def starttls(self):
        self._record("starttls")

    def login(self, sender, password):
        self._record("login", sender, password)

    def send_message(self, message, to_addrs):
        self._record("send_message")
        self.message = message
        self.recipients = to_addrs

    def quit(self):
        self._record("quit")


@pytest.fixture(params=[logging.INFO, logging.WARNING, logging.ERROR])
def diagnostic_threshold(request):
    """Configure and restore the actual diagnostic logger for this unit test."""
    import scitex_logging as slogging

    previous = slogging.get_level()
    slogging.set_level(request.param)
    try:
        yield request.param
    finally:
        slogging.set_level(previous)


def _logger_state():
    """Observe logger configuration, without replacing handlers or streams."""
    from scitex_notification._notify_legacy import log

    root = logging.getLogger()
    return (root.level, log.level, tuple((id(h), h.level) for h in root.handlers))


def test_send_gmail_requested_confirmation_is_verbatim_stdout(
    diagnostic_threshold, capsys
):
    """Requested success output survives INFO/WARNING/ERROR thresholds."""
    # Arrange
    from scitex_notification import send_gmail

    transport = SMTPTranscript()
    before = _logger_state()
    expected = (
        "Email was sent:\n"
        "    sender@example.invalid -> recipient@example.invalid\n"
        "    (ID: public-unit-47)\n\n"
    )

    # Act
    result = send_gmail(
        "sender@example.invalid", "synthetic-password", "recipient@example.invalid",
        "Finished", "Public unit body", ID="public-unit-47", verbose=True,
        smtp_server="smtp.example.invalid", smtp_port=2525, smtp_factory=transport,
    )
    captured = capsys.readouterr()

    # Assert
    assert (result, captured.out, captured.err, transport.calls, _logger_state()) == (
        None, expected, "",
        [("construct", "smtp.example.invalid", 2525), ("starttls",),
         ("login", "sender@example.invalid", "synthetic-password"),
         ("send_message",), ("quit",)], before,
    )


def test_send_gmail_quiet_success_keeps_the_full_synthetic_transaction(
    diagnostic_threshold, capsys
):
    """verbose=False changes output only, including at ERROR."""
    # Arrange
    from scitex_notification import send_gmail

    transport = SMTPTranscript()
    before = _logger_state()

    # Act
    result = send_gmail(
        "sender@gmail.com", "synthetic-password", "recipient@example.invalid",
        "Finished", "Public unit body", verbose=False, smtp_factory=transport,
    )
    captured = capsys.readouterr()

    # Assert
    assert (result, captured.out, captured.err, transport.calls, _logger_state()) == (
        None, "", "",
        [("construct", "smtp.gmail.com", 587), ("starttls",),
         ("login", "sender@gmail.com", "synthetic-password"),
         ("send_message",), ("quit",)], before,
    )


@pytest.mark.parametrize(
    "cc, recipients, cc_header, cc_info",
    [
        (None, ["recipient@example.invalid"], None, ""),
        (
            "copy@example.invalid",
            ["recipient@example.invalid", "copy@example.invalid"],
            "copy@example.invalid",
            " (CC: copy@example.invalid)",
        ),
        (
            ["a@example.invalid", "b@example.invalid"],
            ["recipient@example.invalid", "a@example.invalid", "b@example.invalid"],
            "a@example.invalid, b@example.invalid",
            " (CC: ['a@example.invalid', 'b@example.invalid'])",
        ),
    ],
)
def test_send_gmail_cc_mime_and_summary_are_unchanged(
    cc, recipients, cc_header, cc_info, diagnostic_threshold, capsys
):
    """The actual MIME construction and recipient order remain observable."""
    # Arrange
    from scitex_notification import send_gmail

    transport = SMTPTranscript()
    expected = (
        "Email was sent:\n"
        f"    sender@example.invalid -> recipient@example.invalid{cc_info}\n"
        "    (ID: None)\n\n"
    )

    # Act
    result = send_gmail(
        "sender@example.invalid", "synthetic-password", "recipient@example.invalid",
        "Finished", "日本語 public body", sender_name="Unit Sender", cc=cc,
        smtp_server="smtp.example.invalid", smtp_factory=transport,
    )
    captured = capsys.readouterr()
    message = transport.message

    # Assert
    assert (
        result, captured.out, captured.err, message["Subject"], message["From"],
        message["To"], message["Cc"], transport.recipients,
        message.get_payload()[0].get_payload(decode=True).decode("utf-8"),
    ) == (
        None, expected, "", "Finished", "Unit Sender <sender@example.invalid>",
        "recipient@example.invalid", cc_header, recipients, "日本語 public body",
    )


def test_send_gmail_real_attachment_mime_and_verbatim_paths(
    tmp_path, diagnostic_threshold, capsys
):
    """Actual local log/binary bytes feed MIME; ANSI paths stay verbatim stdout."""
    # Arrange
    from scitex_notification import send_gmail

    log_path = tmp_path / "public.log"
    binary_path = tmp_path / "日本語-\x1b[31mpublic\x1b[0m.bin"
    log_path.write_text("\x1b[31mERROR\x1b[0m done\n", encoding="utf-8")
    binary_path.write_bytes(bytes([0, 1, 2, 255]))
    paths = [str(log_path), str(binary_path)]
    transport = SMTPTranscript()
    expected = (
        "Email was sent:\n"
        "    sender@example.invalid -> recipient@example.invalid\n"
        "    (ID: public-unit-47)\n"
        "    Attached:\n"
        f"        {paths[0]}\n        {paths[1]}\n\n"
    )

    # Act
    result = send_gmail(
        "sender@example.invalid", "synthetic-password", "recipient@example.invalid",
        "", "Public unit body", ID="public-unit-47", attachment_paths=paths,
        smtp_server="smtp.example.invalid", smtp_factory=transport,
    )
    captured = capsys.readouterr()
    parts = transport.message.get_payload()

    # Assert
    assert (
        result, captured.out, captured.err, transport.message["Subject"],
        [part.get_payload(decode=True) for part in parts],
        [part.get_filename() for part in parts[1:]], transport.calls[-1],
    ) == (
        None, expected, "", "ID: public-unit-47",
        [b"Public unit body", b"ERROR done\n", bytes([0, 1, 2, 255])],
        [log_path.name, binary_path.name], ("quit",),
    )


@pytest.mark.parametrize(
    "failure", ["construct", "starttls", "login", "send_message", "quit"]
)
def test_send_gmail_failed_stage_stays_diagnostic_and_never_confirms(
    failure, diagnostic_threshold, capsys
):
    """Synthetic failures retain existing stop/error/None behavior, not delivery."""
    # Arrange
    from scitex_notification import send_gmail

    transport = SMTPTranscript(failure=failure)
    stages = ["construct", "starttls", "login", "send_message", "quit"]
    expected_stages = stages[: stages.index(failure) + 1]
    before = _logger_state()

    # Act
    result = send_gmail(
        "sender@example.invalid", "synthetic-password", "recipient@example.invalid",
        "Finished", "Public unit body", smtp_server="smtp.example.invalid",
        smtp_factory=transport,
    )
    captured = capsys.readouterr()

    # Assert
    assert (
        result, captured.out,
        f"Email was not sent: synthetic {failure} refusal" in captured.err,
        "Email was sent:" in captured.err, [call[0] for call in transport.calls],
        _logger_state(),
    ) == (None, "", True, False, expected_stages, before)
