#!/usr/bin/env python3
# Timestamp: "2026-03-16 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_cli/_mcp_cmds.py

"""CLI subcommands for MCP operations."""

from __future__ import annotations

import json
import sys

import click

from ._helpers import emit_result, group_to_json


@click.group(invoke_without_command=True)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as structured JSON.",
)
@click.pass_context
def mcp(ctx, as_json):
    """MCP (Model Context Protocol) server operations."""
    if ctx.invoked_subcommand is None:
        if as_json:
            group_to_json(ctx, mcp)
        else:
            click.echo(ctx.get_help())


@mcp.command("start")
@click.option("--dry-run", is_flag=True, help="Print launch plan without starting.")
@click.option(
    "-y", "--yes", is_flag=True, help="Suppress interactive confirmation (assume yes)."
)
def mcp_start(dry_run, yes):
    """
    Start the MCP stdio server

    \b
    Example:
      scitex-notification mcp start
      scitex-notification mcp start --dry-run
    """
    if dry_run:
        click.echo(
            "DRY RUN — would start scitex-notification MCP server (stdio transport)"
        )
        return
    from scitex_notification.mcp_server import main as run_server

    run_server()


@mcp.command("doctor")
def mcp_doctor():
    """
    Check MCP server health and dependencies

    \b
    Example:
      scitex-notification mcp doctor
    """
    issues = []

    try:
        import mcp  # noqa: F401

        click.secho("  mcp package: OK", fg="green")
    except ImportError:
        click.secho("  mcp package: MISSING (pip install mcp)", fg="red")
        issues.append("mcp")

    try:
        import scitex_notification as _stxn

        click.secho(f"  scitex-notification: OK (v{_stxn.__version__})", fg="green")
    except Exception as e:
        click.secho(f"  scitex-notification: ERROR ({e})", fg="red")
        issues.append("scitex-notification")

    try:
        from scitex_notification import available_backends

        avail = available_backends()
        if avail:
            click.secho(f"  Available backends: {', '.join(avail)}", fg="green")
        else:
            click.secho("  Available backends: none", fg="yellow")
    except Exception as e:
        click.secho(f"  Backend check failed: {e}", fg="red")

    if issues:
        click.secho(f"\nIssues found: {', '.join(issues)}", fg="red")
        sys.exit(1)
    else:
        click.secho("\nAll checks passed.", fg="green")


@mcp.command(
    "installation", hidden=True, context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def mcp_installation_deprecated(ctx):
    """(deprecated) Renamed to `install`."""
    click.echo(
        "error: `scitex-notification mcp installation` was renamed to "
        "`scitex-notification mcp install`.\n"
        "Re-run with: scitex-notification mcp install",
        err=True,
    )
    ctx.exit(2)


@mcp.command(
    "show-installation", hidden=True, context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def mcp_show_installation_deprecated(ctx):
    """(deprecated) Renamed to `install`."""
    click.echo(
        "error: `scitex-notification mcp show-installation` was renamed to "
        "`scitex-notification mcp install`.\n"
        "Re-run with: scitex-notification mcp install",
        err=True,
    )
    ctx.exit(2)


@mcp.command("install")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--dry-run", is_flag=True, help="Accepted for §2; this verb is informational, never mutates state.")
@click.option("--yes", "-y", is_flag=True, help="Accepted for §2; this verb is informational, never mutates state.")
def mcp_install(as_json, dry_run, yes):
    """
    Show MCP server installation instructions

    \b
    Example:
      scitex-notification mcp install
      scitex-notification mcp install --json
    """
    del dry_run, yes  # audit §2 — no-op flags
    config = {
        "mcpServers": {
            "scitex-notification": {
                "command": "scitex-notification",
                "args": ["mcp", "start"],
            }
        }
    }
    if as_json:
        emit_result(
            {
                "install_command": "pip install scitex-notification[mcp]",
                "config": config,
                "verify_commands": ["scitex-notification mcp doctor"],
            }
        )
        return
    click.secho("Add to your MCP client config (e.g., claude_desktop_config.json):")
    click.echo()
    click.echo(json.dumps(config, indent=2))


@mcp.command("list-tools")
@click.option("-v", "--verbose", count=True, help="Verbosity: -v +desc, -vv +schema")
@click.option("-c", "--compact", is_flag=True, help="Compact output (one line each)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mcp_list_tools(verbose, compact, as_json):
    """
    List available MCP tools

    \b
    Example:
      scitex-notification mcp list-tools
      scitex-notification mcp list-tools -v
      scitex-notification mcp list-tools --json
    """
    _STATIC_TOOLS = [
        "notify",
        "notify_by_level",
        "list_notification_backends",
        "available_notification_backends",
        "get_notification_config",
    ]

    try:
        from scitex_notification._mcp.tool_schemas import get_tool_schemas

        tools = get_tool_schemas()
    except ImportError:
        if as_json:
            emit_result({"tools": _STATIC_TOOLS})
        else:
            click.secho("MCP Tools (scitex-notification):", fg="cyan", bold=True)
            for name in _STATIC_TOOLS:
                click.echo(f"  - {name}")
        return

    if as_json:
        data = []
        for t in tools:
            entry: dict = {"name": t.name}
            if verbose >= 1:
                entry["description"] = t.description
            if verbose >= 2:
                entry["inputSchema"] = t.inputSchema
            data.append(entry)
        emit_result({"tools": data})
    else:
        click.secho("MCP Tools (scitex-notification):", fg="cyan", bold=True)
        for t in tools:
            if compact or verbose == 0:
                click.echo(f"  {t.name}")
            else:
                click.echo(f"\n  {t.name}")
                for line in t.description.split("\n"):
                    click.echo(f"    {line}")


# EOF
