#!/usr/bin/env python3
"""Smoke layer (PS-211): fast subprocess CLI happy-path tests (<60s).

Runs the installed `scitex-notification` console script in a subprocess
with an isolated HOME (see conftest.py) and asserts the happy path stays
green.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

_CONSOLE = shutil.which("scitex-notification")
_BASE_CMD = (
    [_CONSOLE] if _CONSOLE else [sys.executable, "-m", "scitex_notification"]
)


@pytest.mark.smoke
def test_cli_version_reports_package():
    """`--version` must exit 0 and name the distribution."""
    # Arrange
    cmd = [*_BASE_CMD, "--version"]
    # Act
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    # Assert
    assert result.returncode == 0 and "scitex-notification" in result.stdout


@pytest.mark.smoke
def test_list_backends_exits_zero():
    """`list-backends` must exit 0 and show the fallback order."""
    # Arrange
    cmd = [*_BASE_CMD, "list-backends"]
    # Act
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    # Assert
    assert result.returncode == 0 and "Fallback order" in result.stdout


@pytest.mark.smoke
def test_mcp_list_tools_names_notify():
    """`mcp list-tools` must exit 0 and expose the notify tool."""
    # Arrange
    cmd = [*_BASE_CMD, "mcp", "list-tools"]
    # Act
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    # Assert
    assert result.returncode == 0 and "notify" in result.stdout
