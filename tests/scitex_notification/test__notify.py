#!/usr/bin/env python3
# Timestamp: "2026-05-30 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/tests/scitex_notification/test__notify.py

"""Tests for the migrated legacy notify helpers.

Covers the pure, network-free helpers only:
- gen_footer() structure
- get_hostname() / get_username() return non-empty strings
- ansi_escape strips ANSI color codes
- public re-exports (notify, send_gmail) are importable

No email is actually sent — send_gmail/notify network paths are NOT exercised.
"""

from __future__ import annotations

import socket
import types


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
