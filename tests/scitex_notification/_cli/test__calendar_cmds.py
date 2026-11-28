"""`scitex-notification calendar ...` in-process, real environment (no mocks)."""

import json

from click.testing import CliRunner

from scitex_notification._cli import main as cli

AT = "2026-11-28T09:24:40Z"
STAMP = {"dateTime": "2026-11-28T18:24:40+09:00", "timeZone": "Asia/Tokyo"}
ADD = ["calendar", "add-milestone", "-c", "SciTeX R&D", "-t", "A"]


def test_cli_offline_prints_the_event_body():
    # Arrange
    args = ADD + ["--at", AT, "-n", "note", "--offline"]
    # Act
    result = CliRunner().invoke(cli, args)
    # Assert
    assert json.loads(result.output)["event"]["start"] == STAMP


def test_cli_naive_time_exits_2():
    # Arrange
    args = ADD + ["--at", "2026-11-28", "--offline"]
    # Act
    result = CliRunner().invoke(cli, args)
    # Assert
    assert result.exit_code == 2


def test_cli_without_account_fails_loud_with_exit_1(tmp_path):
    # Arrange
    env = {"SCITEX_NOTIFICATION_GCAL_ACCOUNT": None, "SCITEX_DIR": str(tmp_path)}
    # Act
    result = CliRunner(env=env).invoke(cli, ADD + ["--at", AT, "--dry-run"])
    # Assert
    assert (result.exit_code, "ACCOUNT is not set" in result.output) == (1, True)
