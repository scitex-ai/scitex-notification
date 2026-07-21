#!/usr/bin/env python3
# File: /home/ywatanabe/proj/scitex-notification/tests/test_cli.py
"""Tests for the CLI entry point.

Covers:
- --help exits with code 0 and contains usage text
- backends command lists backends
- send --dry-run prints dry-run output without sending
- call --dry-run prints dry-run output without calling
- sms --dry-run prints dry-run output without sending
- config command prints configuration
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from scitex_notification._cli._main import cli

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# test_cli_help
# ---------------------------------------------------------------------------
def test_cli_help_flag_exits_zero(runner):
    """--help should exit 0."""
    # Arrange
    args = ["--help"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_cli_help_flag_shows_usage_text(runner):
    """--help should show usage information."""
    # Arrange
    args = ["--help"]

    # Act
    result = runner.invoke(cli, args)
    shows_usage = "Usage" in result.output or "notification" in result.output.lower()

    # Assert
    assert shows_usage


def test_cli_h_flag_exits_zero(runner):
    """-h should also show help."""
    # Arrange
    args = ["-h"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_cli_no_arguments_exits_zero(runner):
    """Invoking with no args should show help text (exit 0)."""
    # Arrange
    args: list[str] = []

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# test_cli_backends
# ---------------------------------------------------------------------------
def test_cli_list_backends_exits_zero(runner):
    """list-backends command should exit 0."""
    # Arrange
    args = ["list-backends"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_cli_list_backends_prints_output(runner):
    """list-backends command should produce output."""
    # Arrange
    args = ["list-backends"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert len(result.output) > 0


def test_cli_list_backends_json_exits_zero(runner):
    """list-backends --json should exit 0."""
    # Arrange
    args = ["list-backends", "--json"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_cli_list_backends_json_contains_available_key(runner):
    """list-backends --json should output valid JSON with 'available' key."""
    # Arrange
    import json

    args = ["list-backends", "--json"]

    # Act
    result = runner.invoke(cli, args)
    data = json.loads(result.output)
    inner = data.get("data", data)
    has_key = "available" in inner or "available_backends" in inner

    # Assert
    assert has_key


# ---------------------------------------------------------------------------
# test_send_dry_run
# ---------------------------------------------------------------------------
def test_send_dry_run_exits_zero(runner):
    """send --dry-run should exit 0."""
    # Arrange
    args = ["send-notification", "Test message", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_send_dry_run_emits_dry_run_marker(runner):
    """send --dry-run should print dry-run marker."""
    # Arrange
    args = ["send-notification", "Test message", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "dry-run" in result.output


def test_send_dry_run_echoes_message(runner):
    """send --dry-run should echo the message body."""
    # Arrange
    args = ["send-notification", "Test message", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "Test message" in result.output


def test_send_dry_run_with_backend_exits_zero(runner):
    """send --dry-run --backend desktop should exit 0."""
    # Arrange
    args = ["send-notification", "Hello", "--dry-run", "--backend", "desktop"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_send_dry_run_with_backend_emits_dry_run_marker(runner):
    """send --dry-run --backend desktop should mention dry-run."""
    # Arrange
    args = ["send-notification", "Hello", "--dry-run", "--backend", "desktop"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "dry-run" in result.output


def test_send_dry_run_with_level_exits_zero(runner):
    """send --dry-run --level error should exit 0."""
    # Arrange
    args = ["send-notification", "Error msg", "--dry-run", "--level", "error"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_send_dry_run_with_level_emits_dry_run_marker(runner):
    """send --dry-run --level error should mention dry-run."""
    # Arrange
    args = ["send-notification", "Error msg", "--dry-run", "--level", "error"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "dry-run" in result.output


# ---------------------------------------------------------------------------
# test_call_dry_run
# ---------------------------------------------------------------------------
def test_call_dry_run_exits_zero(runner):
    """call --dry-run should exit 0."""
    # Arrange
    args = ["call", "Wake up!", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_call_dry_run_emits_dry_run_marker(runner):
    """call --dry-run should print dry-run marker."""
    # Arrange
    args = ["call", "Wake up!", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "dry-run" in result.output


def test_call_dry_run_echoes_message(runner):
    """call --dry-run should echo the message body."""
    # Arrange
    args = ["call", "Wake up!", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "Wake up!" in result.output


def test_call_dry_run_with_repeat_exits_zero(runner):
    """call --dry-run --repeat 2 should exit 0."""
    # Arrange
    args = ["call", "Hello", "--dry-run", "--repeat", "2"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_call_dry_run_with_repeat_emits_dry_run_marker(runner):
    """call --dry-run --repeat 2 should mention dry-run."""
    # Arrange
    args = ["call", "Hello", "--dry-run", "--repeat", "2"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "dry-run" in result.output


# ---------------------------------------------------------------------------
# test_sms_dry_run
# ---------------------------------------------------------------------------
def test_sms_dry_run_exits_zero(runner):
    """sms --dry-run should exit 0."""
    # Arrange
    args = ["send-sms", "Build done!", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_sms_dry_run_emits_dry_run_marker(runner):
    """sms --dry-run should print dry-run marker."""
    # Arrange
    args = ["send-sms", "Build done!", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "dry-run" in result.output


def test_sms_dry_run_echoes_message(runner):
    """sms --dry-run should echo the message body."""
    # Arrange
    args = ["send-sms", "Build done!", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "Build done!" in result.output


def test_sms_dry_run_with_title_exits_zero(runner):
    """sms --dry-run --title prepends title context."""
    # Arrange
    args = ["send-sms", "Finished", "--dry-run", "--title", "CI"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_sms_dry_run_with_title_emits_dry_run_marker(runner):
    """sms --dry-run --title prints dry-run."""
    # Arrange
    args = ["send-sms", "Finished", "--dry-run", "--title", "CI"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "dry-run" in result.output


# ---------------------------------------------------------------------------
# test_config_command
# ---------------------------------------------------------------------------
def test_show_config_command_exits_zero(runner):
    """show-config should exit 0."""
    # Arrange
    args = ["show-config"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_show_config_command_emits_output(runner):
    """show-config should display configuration."""
    # Arrange
    args = ["show-config"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert len(result.output) > 0


def test_show_config_json_exits_zero(runner):
    """show-config --json should exit 0."""
    # Arrange
    args = ["show-config", "--json"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_show_config_json_contains_default_backend(runner):
    """show-config --json should include default_backend key."""
    # Arrange
    import json

    args = ["show-config", "--json"]

    # Act
    result = runner.invoke(cli, args)
    data = json.loads(result.output)
    inner = data.get("data", data)

    # Assert
    assert "default_backend" in inner


# ---------------------------------------------------------------------------
# test_help_recursive
# ---------------------------------------------------------------------------
def test_help_recursive_flag_exits_zero(runner):
    """--help-recursive should show recursive help and exit 0."""
    # Arrange
    args = ["--help-recursive"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# test_list_python_apis
# ---------------------------------------------------------------------------
def test_list_python_apis_exits_zero(runner):
    """list-python-apis should exit 0."""
    # Arrange
    args = ["list-python-apis"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_list_python_apis_lists_package_name(runner):
    """list-python-apis should mention scitex_notification."""
    # Arrange
    args = ["list-python-apis"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "scitex_notification" in result.output


def test_list_python_apis_json_exits_zero(runner):
    """list-python-apis --json should exit 0."""
    # Arrange
    args = ["list-python-apis", "--json"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_list_python_apis_json_contains_apis_key(runner):
    """list-python-apis --json should return JSON with 'apis' key."""
    # Arrange
    import json

    args = ["list-python-apis", "--json"]

    # Act
    result = runner.invoke(cli, args)
    data = json.loads(result.output)

    # Assert
    assert "apis" in data


# ---------------------------------------------------------------------------
# test_send_is_canonical  (send replaces send-notification as the verb leaf)
# ---------------------------------------------------------------------------
def test_send_canonical_command_dry_run_exits_zero(runner):
    """The canonical `send <message>` command works (exit 0 on dry-run)."""
    # Arrange
    args = ["send", "Canonical send", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_send_canonical_command_echoes_message(runner):
    """`send` echoes the message body in dry-run output."""
    # Arrange
    args = ["send", "Canonical send", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "Canonical send" in result.output


def test_send_listed_in_top_level_help(runner):
    """`send` is advertised in the top-level command list (canonical leaf)."""
    # Arrange
    args = ["--help"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "send" in result.output


def test_send_notification_alias_still_works_dry_run(runner):
    """The old `send-notification` name keeps working as a back-compat alias."""
    # Arrange
    args = ["send-notification", "Alias send", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert result.exit_code == 0


def test_send_notification_alias_echoes_message(runner):
    """The alias produces the same dry-run echo as the canonical command."""
    # Arrange
    args = ["send-notification", "Alias send", "--dry-run"]

    # Act
    result = runner.invoke(cli, args)

    # Assert
    assert "Alias send" in result.output


# ---------------------------------------------------------------------------
# test_send_explicit_unavailable_backend_fails_loud  (no silent emacs fallback)
# ---------------------------------------------------------------------------
@pytest.fixture
def unavailable_backend_send_result(runner):
    """Run `send --backend email` with the email backend forced unavailable.

    `email` is already a valid --backend choice, so we don't fight
    ``click.Choice``: we just swap the registry's ``email`` entry for a real,
    never-available backend for the duration of the test. That drives the
    explicit-backend fail-loud path (exit 1 + clear message), proving the CLI
    does NOT silently fall back to emacs. Restores the registry on teardown.
    """
    from datetime import datetime

    from scitex_notification._backends import BACKENDS
    from scitex_notification._backends._types import (
        BaseNotifyBackend,
        NotifyResult,
    )

    class _NeverAvailEmail(BaseNotifyBackend):
        name = "email"

        def is_available(self) -> bool:
            return False

        async def send(self, message, title=None, level=None, **kwargs):
            return NotifyResult(
                success=False,
                backend=self.name,
                message=message,
                timestamp=datetime.now().isoformat(),
                error="never",
            )

    backends_snapshot = dict(BACKENDS)
    BACKENDS["email"] = _NeverAvailEmail
    try:
        result = runner.invoke(cli, ["send", "must fail loud", "--backend", "email"])
        yield result
    finally:
        BACKENDS.clear()
        BACKENDS.update(backends_snapshot)


def test_send_explicit_unavailable_backend_exits_nonzero(
    unavailable_backend_send_result,
):
    """Explicit unavailable backend exits non-zero (never a quiet emacs swap)."""
    # Arrange
    result = unavailable_backend_send_result

    # Act
    exit_code = result.exit_code

    # Assert
    assert exit_code != 0


def test_send_explicit_unavailable_backend_reports_failure_text(
    unavailable_backend_send_result,
):
    """The failure message is shown, not a misleading 'Notification sent'."""
    # Arrange
    result = unavailable_backend_send_result

    # Act
    says_failed = "Failed to send notification" in result.output

    # Assert
    assert says_failed is True


# EOF
