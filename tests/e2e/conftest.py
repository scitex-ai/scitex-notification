"""Isolation for the e2e layer: HOME at a tmp dir, Agg canvas.

The matplotlib backend renders offscreen under MPLBACKEND=Agg so the
suite runs headless with no display and no network. Explicit
save/restore (no monkeypatch, PA-306).
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolated_headless_env(tmp_path):
    previous = {
        name: os.environ.get(name) for name in ("HOME", "MPLBACKEND")
    }
    os.environ["HOME"] = str(tmp_path)
    os.environ["MPLBACKEND"] = "Agg"
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
