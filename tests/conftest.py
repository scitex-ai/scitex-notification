"""Module-import-time coverage wiring (parallel + subprocess support).

`os.environ.setdefault` would be a no-op here because pytest-cov has
already set ``COVERAGE_FILE`` to a tmp dir by the time conftest is loaded.

See ``scitex_dev._skills.general.05_development_06_subprocess-coverage``.
"""
from __future__ import annotations

import os
import sysconfig
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

os.environ["COVERAGE_PROCESS_START"] = str(_PROJECT_ROOT / "pyproject.toml")
os.environ["COVERAGE_FILE"] = str(_PROJECT_ROOT / ".coverage")


def _ensure_subprocess_coverage_shim() -> None:
    purelib = Path(sysconfig.get_paths()["purelib"])
    pth = purelib / "_scitex_notification_subprocess_coverage.pth"
    shim = (
        "import os, coverage\n"
        "if os.environ.get('COVERAGE_PROCESS_START'):\n"
        "    coverage.process_startup()\n"
    )
    try:
        if not pth.exists() or pth.read_text() != shim:
            pth.write_text(shim)
    except OSError:
        pass


_ensure_subprocess_coverage_shim()


# ===== existing conftest content below =====
"""Pytest fixtures and rootdir marker for this package.

An empty conftest.py at tests/ is the canonical SciTeX
convention (audit-project PS208) — it pins the pytest
rootdir and gives downstream fixtures a home.
"""
