"""Tests for the template / profile CLI commands (real click invocation)."""

import json

from click.testing import CliRunner

from scitex_notification._cli._main import cli

DATA = {
    "kind": "DONE",
    "title": "release 1.2.3",
    "done": ["published https://example.org/r/1"],
    "meta": {"agent": "worker-1", "host": "h1", "refs": "#5"},
}
PROFILE_ENV = {
    "SCITEX_NOTIFICATION_PROFILE_CLITEST_FROM": "no-reply@example.org",
    "SCITEX_NOTIFICATION_PROFILE_CLITEST_TO": "dev@example.org",
    "SCITEX_NOTIFICATION_PROFILE_CLITEST_SMTP_HOST": "127.0.0.1",
    "SCITEX_NOTIFICATION_PROFILE_CLITEST_SMTP_PORT": "1",
    "SCITEX_NOTIFICATION_PROFILE_CLITEST_PASSWORD": "local-test-only",
}


def _run(args, env=None):
    return CliRunner().invoke(cli, args, env=env)


def test_render_message_prints_subject_and_body(tmp_path):
    # Arrange
    (tmp_path / "n.json").write_text(json.dumps(DATA))
    # Act
    result = _run(["render-message", str(tmp_path / "n.json")])
    # Assert
    assert json.loads(result.output)["subject"] == "[SciTeX][worker-1] DONE: release 1.2.3"


def test_validate_message_exits_2_and_lists_violations(tmp_path):
    # Arrange
    (tmp_path / "b.txt").write_text("hello\n")
    # Act
    result = _run(["validate-message", "-s", "hi", "-f", str(tmp_path / "b.txt")])
    # Assert
    assert (result.exit_code, "footer missing" in result.output) == (2, True)


def test_list_templates_includes_notice():
    # Arrange
    args = ["list-templates", "--json"]
    # Act
    result = _run(args)
    # Assert
    assert "notice" in json.loads(result.output)["templates"]


def test_show_profile_never_prints_the_password():
    # Arrange
    args = ["show-profile", "clitest", "--json"]
    # Act
    result = _run(args, env=PROFILE_ENV)
    # Assert
    assert (result.exit_code, "local-test-only" in result.output) == (0, False)


def test_send_email_dry_run_renders_and_reports(tmp_path):
    # Arrange
    (tmp_path / "n.json").write_text(json.dumps(DATA))
    args = ["send-email", "-p", "clitest", "-t", "notice"]
    args += ["--data-file", str(tmp_path / "n.json"), "--dry-run"]
    # Act
    result = _run(args, env=PROFILE_ENV)
    # Assert
    assert json.loads(result.output)["status"] == "dry_run"


def test_send_email_unknown_profile_exits_2(tmp_path):
    # Arrange
    (tmp_path / "b.txt").write_text("hello\n")
    args = ["send-email", "-p", "nosuchprofile", "-s", "x", "-f", str(tmp_path / "b.txt")]
    # Act
    result = _run(args)
    # Assert
    assert result.exit_code == 2
