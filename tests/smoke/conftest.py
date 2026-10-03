"""Isolation for the smoke layer: point HOME at a tmp dir.

The CLI reads user-wide config from the home directory; with HOME
redirected the suite exercises built-in defaults and never touches the
operator's real state. Explicit save/restore (no monkeypatch, PA-306).
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path):
    previous = os.environ.get("HOME")
    os.environ["HOME"] = str(tmp_path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = previous
