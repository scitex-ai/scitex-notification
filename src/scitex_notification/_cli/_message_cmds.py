#!/usr/bin/env python3
# File: src/scitex_notification/_cli/_message_cmds.py

"""CLI: message templates, email profiles, and profile sends.

Exit codes: 0 ok, 1 send failure, 2 invalid input (format violation,
unknown template, unusable profile).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


def _emit(payload: dict) -> None:
    click.echo(json.dumps(payload, ensure_ascii=False))


def _invalid(message: str) -> None:
    click.echo(f"error: {message}", err=True)
    sys.exit(2)


def _render_or_read(template, data_file, subject, body_file):
    """(subject, body) from --data-file (rendered) or --subject/--body-file."""
    from scitex_notification import load_message_data, render_template

    if data_file and (subject or body_file):
        _invalid("pass either --data-file or --subject/--body-file, not both")
    if data_file:
        if not template:
            _invalid("--data-file needs --template")
        return render_template(template, load_message_data(data_file))
    if not subject or not body_file:
        _invalid("pass --data-file, or both --subject and --body-file")
    return subject, Path(body_file).read_text(encoding="utf-8")


def _guard(func, *args, **kwargs):
    from scitex_notification import MessageFormatError, ProfileError

    try:
        return func(*args, **kwargs)
    except (MessageFormatError, ProfileError, KeyError, ValueError) as exc:
        _invalid(str(exc).strip("'\""))


@click.command("list-templates")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_templates_cmd(as_json):
    """List registered message templates (built-in: notice).

    \b
    Example:
      $ scitex-notification list-templates --json
    """
    from scitex_notification import list_templates

    names = list_templates()
    if as_json:
        _emit({"templates": names})
    else:
        for name in names:
            click.echo(name)


@click.command("render-message")
@click.argument("data_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--template", "-t", default="notice", show_default=True)
def render_message(data_file, template):
    """Render DATA_FILE (JSON or YAML) with a template and validate it.

    \b
    Example:
      scitex-notification render-message notice.json
    """
    from scitex_notification import load_message_data, render_template

    subject, body = _guard(
        lambda: render_template(template, load_message_data(data_file))
    )
    _emit({"template": template, "subject": subject, "body": body})


@click.command("validate-message")
@click.option("--template", "-t", default="notice", show_default=True)
@click.option("--subject", "-s", required=True)
@click.option(
    "--body-file", "-f", required=True, type=click.Path(exists=True, dir_okay=False)
)
@click.option("--agent", help="Also require the subject/footer to name this agent.")
def validate_message_cmd(template, subject, body_file, agent):
    """Validate an already-written subject and body; exit 2 listing violations.

    \b
    Example:
      $ scitex-notification validate-message -s "[SciTeX][w1] DONE: x" -f body.txt
    """
    from scitex_notification import validate_message

    body = Path(body_file).read_text(encoding="utf-8")
    context = {"agent": agent} if agent else {}
    _guard(validate_message, template, subject, body, **context)
    _emit({"template": template, "valid": True})


@click.command("show-profile")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def show_profile(name, as_json):
    """Show email profile NAME from SCITEX_NOTIFICATION_PROFILE_<NAME>_* (no secret).

    \b
    Example:
      $ scitex-notification show-profile ops --json
    """
    from scitex_notification import get_profile

    summary = _guard(get_profile, name).describe()
    if as_json:
        _emit(summary)
    else:
        for key, value in summary.items():
            click.echo(f"{key}: {value}")


@click.command("send-email")
@click.option("--profile", "-p", required=True, help="Profile name (see show-profile).")
@click.option(
    "--template", "-t", help="Validate (and with --data-file render) with it."
)
@click.option("--data-file", type=click.Path(exists=True, dir_okay=False))
@click.option("--subject", "-s")
@click.option("--body-file", "-f", type=click.Path(exists=True, dir_okay=False))
@click.option("--message-id", help="Explicit Message-ID, <local@domain>.")
@click.option("--dedupe-key", help="Send at most once per key per --dedupe-window.")
@click.option("--dedupe-window", type=float, help="Window in seconds for --dedupe-key.")
@click.option("--dry-run", is_flag=True, help="Validate and report; never connect.")
@click.option(
    "-y", "--yes", is_flag=True, help="Suppress interactive confirmation (none is asked)."
)
def send_email_cmd(
    yes,
    profile,
    template,
    data_file,
    subject,
    body_file,
    message_id,
    dedupe_key,
    dedupe_window,
    dry_run,
):
    """Send one email as a configured profile.

    \b
    Examples:
      scitex-notification send-email -p ops -s "disk 91% on /data" -f alarm.txt \\
          --dedupe-key disk:/data --dedupe-window 3600
      scitex-notification send-email -p operator -t notice --data-file n.json --dry-run
    """
    from scitex_notification import send_with_profile

    subject, body = _render_or_read(template, data_file, subject, body_file)
    try:
        result = _guard(
            send_with_profile,
            profile,
            subject,
            body,
            message_id=message_id,
            dedupe_key=dedupe_key,
            dedupe_window_s=dedupe_window,
            dry_run=dry_run,
            template=template,
        )
    except OSError as exc:  # smtplib errors are OSError subclasses
        _emit({"status": "failed", "error_type": type(exc).__name__})
        sys.exit(1)
    _emit(result)


COMMANDS = [
    list_templates_cmd,
    render_message,
    validate_message_cmd,
    show_profile,
    send_email_cmd,
]

# EOF
