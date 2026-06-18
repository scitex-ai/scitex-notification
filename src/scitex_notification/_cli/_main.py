#!/usr/bin/env python3
# Timestamp: "2026-03-16 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_cli/_main.py

"""
SciTeX Notification CLI - main entry point.

Composes sub-command modules into the top-level `cli` group.
"""

from __future__ import annotations

import inspect

import click

from ._helpers import group_to_json, print_help_recursive
from ._mcp_cmds import mcp
from ._notify_cmds import (  # noqa: F401
    call,
    list_backends,
    send_notification,
    send_notification_alias,
    send_sms,
    show_config,
)


def _deprecated_redirect(old: str, new: str):
    """Build a hidden Click command that exits 2 with a re-run hint."""

    @click.pass_context
    def _impl(ctx, **_):
        click.echo(
            f"error: `scitex-notification {old}` was renamed to "
            f"`scitex-notification {new}`.\n"
            f"Re-run with: scitex-notification {new} <args>",
            err=True,
        )
        ctx.exit(2)

    return click.command(
        old,
        hidden=True,
        context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    )(_impl)


def _get_version() -> str:
    try:
        from importlib.metadata import version

        return version("scitex-notification")
    except Exception:
        return "0.0.0"


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.version_option(
    _get_version(), "-V", "--version", prog_name="scitex-notification"
)
@click.option("--help-recursive", is_flag=True, help="Show help for all subcommands")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as structured JSON (Result envelope).",
)
@click.pass_context
def cli(ctx, help_recursive, as_json):
    """
    Notification and alerting tools

    \b
    Config is loaded with the SciTeX precedence chain:
      config.yaml -> $SCITEX_NOTIFICATION_CONFIG -> ~/.scitex/notification/config.yaml -> defaults

    \b
    Backends (fallback order):
      audio      - Text-to-Speech (fast, non-blocking)
      emacs      - Emacs minibuffer message
      matplotlib - Visual popup
      playwright - Browser popup
      email      - SMTP email (slowest, most reliable)
      twilio     - Phone call (explicit only)

    \b
    Examples:
      scitex-notification send "Task complete!"
      scitex-notification send "Listen up" --backend audio
      scitex-notification call "Wake up!"
      scitex-notification call "Wake up!" --repeat 2
      scitex-notification list-backends
    """
    if help_recursive:
        print_help_recursive(ctx, cli)
        ctx.exit(0)
    elif ctx.invoked_subcommand is None:
        if as_json:
            group_to_json(ctx, cli)
        else:
            click.echo(ctx.get_help())


# Register sub-commands.
#   `send` is canonical (verb + required positional MESSAGE, per the
#   noun-verb CLI convention — like `install <pkg>`). `send-notification` is
#   kept as a hidden, fully-working back-compat alias so old scripts/agents
#   keep firing. The other renames stay hard-error redirects.
cli.add_command(send_notification)
cli.add_command(send_notification_alias)
cli.add_command(call)
cli.add_command(send_sms)
cli.add_command(list_backends)
cli.add_command(show_config)
cli.add_command(_deprecated_redirect("sms", "send-sms"))
cli.add_command(_deprecated_redirect("backends", "list-backends"))
cli.add_command(_deprecated_redirect("config", "show-config"))

# Register mcp subgroup from _mcp_cmds
cli.add_command(mcp)


@cli.group("telegram-channel")
def telegram_channel_group():
    """Telegram channel for Claude Code (bidirectional chat)."""
    pass


@telegram_channel_group.command("start")
@click.option("--dry-run", is_flag=True, help="Print launch plan without starting.")
@click.option(
    "-y", "--yes", is_flag=True, help="Suppress interactive confirmation (assume yes)."
)
def telegram_channel_start(dry_run, yes):
    """Start the Telegram channel MCP server for Claude Code.

    \b
    Example:
      $ scitex-notification telegram-channel start
      $ scitex-notification telegram-channel start --dry-run
    """
    if dry_run:
        click.echo("DRY RUN — would start Telegram channel MCP server")
        return
    from ..telegram_channel import main as _telegram_main

    _telegram_main()


try:
    from scitex_dev.cli import docs_click_group

    cli.add_command(docs_click_group(package="scitex-notification"))
except ImportError:
    pass

try:
    from scitex_dev.cli import skills_click_group

    cli.add_command(skills_click_group(package="scitex-notification"))
except ImportError:
    pass


@cli.command("list-python-apis")
@click.option("-v", "--verbose", count=True, help="Verbosity: -v +doc, -vv full doc")
@click.option("-d", "--max-depth", type=int, default=3, help="Max recursion depth")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_python_apis(verbose, max_depth, as_json):
    """
    List Python public APIs of scitex_notification

    \b
    Examples:
      scitex-notification list-python-apis
      scitex-notification list-python-apis -v
      scitex-notification list-python-apis --json
    """
    import json as _json

    import scitex_notification

    def _collect(obj, prefix, depth, results):
        if depth > max_depth:
            return
        for name in dir(obj):
            if name.startswith("_"):
                continue
            try:
                attr = getattr(obj, name)
            except Exception:
                continue
            full_name = f"{prefix}.{name}"
            if inspect.isfunction(attr) or inspect.isbuiltin(attr):
                doc = ""
                if verbose >= 1:
                    raw = (inspect.getdoc(attr) or "").strip()
                    doc = raw if verbose >= 2 else raw.split("\n")[0]
                results.append({"name": full_name, "type": "function", "doc": doc})
            elif inspect.ismodule(attr) and attr.__name__.startswith(
                "scitex_notification"
            ):
                _collect(attr, full_name, depth + 1, results)

    results: list[dict] = []
    _collect(scitex_notification, "scitex_notification", 1, results)

    if as_json:
        click.echo(_json.dumps({"success": True, "apis": results}, indent=2))
    else:
        click.secho("Python APIs (scitex_notification):", fg="cyan", bold=True)
        for item in results:
            if item["doc"]:
                click.echo(f"  {item['name']}  - {item['doc']}")
            else:
                click.echo(f"  {item['name']}")


# §1a: install-shell-completion + print-shell-completion (canonical leaves)
try:
    from scitex_dev._cli._completion import attach_shell_completion

    attach_shell_completion(cli, prog_name="scitex-notification")
except ImportError:
    pass


if __name__ == "__main__":
    cli()


# EOF
