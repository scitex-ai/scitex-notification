#!/usr/bin/env bash
# Runs INSIDE the reused scitex-ci SIF (apptainer exec — invoked via
# exec-in-sif.sh). Builds scitex-notification's wheel + sdist into ./dist/.
#
# Use the baked interpreter and install the PEP 517 frontend plus the genuinely
# published auditor into an owned target. The outer verified wrapper binds
# fresh RUNNER_TEMP scratch over container /tmp; HOME and the image stay intact.
# A missing interpreter, dependency or artifact is a hard failure.
set -euo pipefail

V="${1:-3.12}"
VENV="/opt/venv-$V"
PY="$VENV/bin/python"
test -x "$PY" || {
    echo "::error::baked python missing in $VENV — rebuild the SIF: scitex-container apptainer build ci-cpu"
    exit 1
}

export LC_ALL=C.UTF-8 LANG=C.UTF-8

# The outer wrapper makes container /tmp this job's fresh owned scratch.
TMPDIR="/tmp/build-scitex_notification-${GITHUB_RUN_ID:-0}-${GITHUB_RUN_ATTEMPT:-0}-$V"
export TMPDIR
rm -rf "${TMPDIR:?Notification build scratch is empty}"
mkdir -p "$TMPDIR/site" "$TMPDIR/uv-cache" "$TMPDIR/scitex" "$TMPDIR/pycache"
export SCITEX_DIR="$TMPDIR/scitex"
export PYTHONPYCACHEPREFIX="$TMPDIR/pycache"

# The compute-node $HOME is RO inside the container — point every cache the
# installer might touch at the writable scratch (else uv/pip die creating
# ~/.cache).
export UV_CACHE_DIR="$TMPDIR/uv-cache"
export XDG_CACHE_HOME="$TMPDIR"
export PIP_CACHE_DIR="$TMPDIR/pip-cache"

# A VIRTUAL_ENV leaked from the runner profile (~/.env-3.11) is a broken
# symlink in here; unset it so no tool follows it.
unset VIRTUAL_ENV || true

export PATH="$VENV/bin:$PATH"
echo "build: py=$("$PY" -V) target=$TMPDIR/site"

# Install the complete PEP 517 frontend and auditor, then build with them.
# Clean dist/ first so only the freshly
# built artifacts are uploaded.
uv pip install --python "$PY" --target="$TMPDIR/site" build "scitex-dev>=0.62.1"

export PYTHONPATH="$TMPDIR/site${PYTHONPATH:+:$PYTHONPATH}"

rm -rf dist
"$PY" -m build --outdir dist

echo "=== built artifacts ==="
ls -l dist
# fail-loud: refuse to continue the pipeline with an empty dist/.
test -n "$(ls -A dist 2>/dev/null)" || {
    echo "::error::python -m build produced no artifacts in dist/"
    exit 1
}

# Validate the actual built distribution and import its own declared entry points.
WHEEL="$(find dist -maxdepth 1 -name '*.whl' -print -quit)"
[ -n "$WHEEL" ] || { echo "::error::no Notification wheel was built"; exit 1; }
"$PY" - "$WHEEL" "${2:-}" <<'PYGATE'
from email.parser import BytesParser
from importlib.metadata import version
from packaging.version import Version
from pathlib import Path
import sys
import tomllib
import zipfile
from scitex_dev._release.entrypoint_imports import audit_wheel_entry_point_imports
assert Version(version("scitex-dev")) >= Version("0.62.1")
expected = tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
with zipfile.ZipFile(sys.argv[1]) as archive:
    name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
    metadata = BytesParser().parsebytes(archive.read(name))
assert metadata["Name"] == "scitex-notification" and metadata["Version"] == expected
if sys.argv[2]:
    assert sys.argv[2] == "v" + expected, "release tag/source version mismatch"
report = audit_wheel_entry_point_imports(Path(sys.argv[1]), "scitex-notification")
print(report.report())
if not report.is_clean:
    raise SystemExit(1)
PYGATE
