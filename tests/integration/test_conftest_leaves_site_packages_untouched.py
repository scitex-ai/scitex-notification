"""Regression test: importing tests/conftest.py must not touch site-packages."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CONFTEST_PATH = Path(__file__).resolve().parents[1] / "conftest.py"

_CHILD_CODE = """\
import os
import runpy
import site
import sys
from pathlib import Path

conftest = Path(sys.argv[1])

os.environ["COVERAGE_PROCESS_START"] = "SENTINEL_PROCESS_START"
os.environ["COVERAGE_FILE"] = "SENTINEL_COVERAGE_FILE"


def _snapshot():
    names = {}
    dirs = []
    try:
        dirs.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        dirs.append(site.getusersitepackages())
    except Exception:
        pass
    for d in dirs:
        try:
            names[str(d)] = sorted(p.name for p in Path(d).iterdir())
        except OSError:
            names[str(d)] = None
    return names


before = _snapshot()
runpy.run_path(str(conftest))
after = _snapshot()

assert before == after, f"site-packages changed: {before!r} != {after!r}"
assert os.environ.get("COVERAGE_PROCESS_START") == "SENTINEL_PROCESS_START", (
    "COVERAGE_PROCESS_START was overwritten by conftest"
)
assert os.environ.get("COVERAGE_FILE") == "SENTINEL_COVERAGE_FILE", (
    "COVERAGE_FILE was overwritten by conftest"
)
"""


def test_conftest_leaves_site_packages_untouched():
    # Arrange
    cmd = [sys.executable, "-c", _CHILD_CODE, str(CONFTEST_PATH)]
    # Act
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # Assert
    assert proc.returncode == 0, (
        f"child failed with exit {proc.returncode}\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )
