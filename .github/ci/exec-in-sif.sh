#!/usr/bin/env bash
# Outer apptainer-exec wrapper for scitex-notification's self-hosted CI.
#
# Runs ON THE RUNNER (outside the SIF). Resolves apptainer + the SIF image, then
# `apptainer exec`s the SIF and hands off to an INNER script (run inside the
# container). Keeps every workflow job's YAML down to one line —
# `bash .github/ci/exec-in-sif.sh <inner-script> [args...]` — and concentrates
# all the SIF plumbing (apptainer resolution, ~-expansion, scratch, binds) in
# one version-controlled place.
#
# HOST-AGNOSTIC. This script is NOT Spartan-only: it auto-adapts to whichever
# self-hosted runner picks the job up, keyed off what actually exists on the box.
#
#   * Spartan HPC — the GPFS project dir /data/gpfs/projects/punim0264 EXISTS:
#     apptainer comes from the ~/.env-3.11 shim named by SCITEX_CI_APPTAINER,
#     job scratch comes from RUNNER_TEMP, and punim0264 is bound into
#     the container ($HOME/.scitex there is a symlink into it, so without the
#     bind the symlink dangles inside the SIF).
#
#   * Local compute nodes (scitex-compute-01..04) — NO /data/gpfs at all:
#     apptainer is the distro package on PATH (/usr/bin/apptainer), scratch is
#     job-owned under RUNNER_TEMP, and the GPFS bind is OMITTED
#     (apptainer refuses a bind whose source does not exist, and `mkdir -p` on a
#     GPFS scratch path would hard-fail here under `set -e`).
#
# Each of those three decisions (interpreter, scratch, bind) is made
# INDEPENDENTLY from a probe of this host, so a runner that matches neither
# profile exactly still gets a coherent command line.
#
# Env (set by the workflow from repo Actions Variables):
#   SCITEX_CI_APPTAINER   OPTIONAL path to an apptainer shim
#                         (e.g. ~/.env-3.11/bin/apptainer). Honoured when it
#                         points at an executable; otherwise apptainer is taken
#                         from PATH.
#   RUNNER_TEMP           REQUIRED existing spacious job scratch parent
#                         (configured by the runner, not a HOME fallback).
#   SCITEX_CI_SIF         REQUIRED path to the CI SIF image
#                         (e.g. ~/.scitex/dev/containers/ci-cpu.sif)
#
# Usage:
#   bash .github/ci/exec-in-sif.sh run-in-sif.sh 3.12
#
# Fail-loud (operator directive): if NEITHER the shim nor PATH yields an
# apptainer, or the SIF is missing, that is a HARD error naming what was tried
# — never a silent fallback to a bare-runner install.
set -euo pipefail

INNER="${1:?inner script name required (relative to .github/ci/)}"
shift || true

# Spartan's job shell is --noprofile --norc (no Lmod), so its apptainer shim dir
# must be put on PATH explicitly; the shim execs the real Apptainer binary.
# Harmless where that directory is absent — a non-existent PATH entry is simply
# never matched — which is the case on the local compute nodes.
export PATH="$HOME/.env-3.11/bin:$PATH"

# ~-expand the Actions-Variable paths: a quoted "~/…" is NOT tilde-expanded by
# the shell, so substitute a leading ~ with $HOME ourselves.
APPTAINER_VAR="${SCITEX_CI_APPTAINER:-}"
APPTAINER_VAR="${APPTAINER_VAR/#\~/$HOME}"
SIF="${SCITEX_CI_SIF:?SCITEX_CI_SIF not set (repo Actions Variable)}"
SIF="${SIF/#\~/$HOME}"
SIF_SHA256="${SCITEX_CI_SIF_SHA256:?SCITEX_CI_SIF_SHA256 not set (repo Actions Variable)}"

# Apptainer resolution, in order:
#   1. SCITEX_CI_APPTAINER when it names an executable  (Spartan's shim)
#   2. `apptainer` on PATH                              (local compute nodes)
# Only when NEITHER resolves is this an error — and the message names BOTH
# attempts, because "which one did you even try" is the whole diagnosis.
if [ -n "$APPTAINER_VAR" ] && [ -x "$APPTAINER_VAR" ]; then
    APPTAINER="$APPTAINER_VAR"
    APPTAINER_FROM="SCITEX_CI_APPTAINER"
elif APPTAINER="$(command -v apptainer 2>/dev/null)"; then
    APPTAINER_FROM="PATH"
else
    echo "::error::no apptainer on this runner. Tried (1) SCITEX_CI_APPTAINER=${SCITEX_CI_APPTAINER:-<unset>} (expanded to '${APPTAINER_VAR:-<empty>}') — not an executable; (2) 'apptainer' on PATH ($PATH) — not found. Install apptainer on this runner, or point SCITEX_CI_APPTAINER at a working shim. Running the job outside the SIF on a bare-runner install is NOT an acceptable fallback."
    exit 1
fi

[ -f "$SIF" ] || {
    echo "::error::CI SIF missing at $SIF — rebuild it: scitex-container apptainer build ci-cpu"
    exit 1
}

ACTUAL_SIF_SHA256="$(sha256sum "$SIF" | awk '{print $1}')"
if [ "$ACTUAL_SIF_SHA256" != "$SIF_SHA256" ]; then
    echo "::error::CI SIF digest mismatch at $SIF: expected $SIF_SHA256, got $ACTUAL_SIF_SHA256. Synchronize the versioned image before accepting jobs; running an unverified image is forbidden."
    exit 1
fi

# Use a new directory under the runner's spacious job area. Neither root /tmp
# nor HOME caches are acceptable implicit fallbacks. Refuse before execution if
# the configured job parent is missing or cannot stage the full declared tests.
CI_JOB_BASE="${RUNNER_TEMP:?RUNNER_TEMP must name spacious job scratch}"
case "$CI_JOB_BASE" in
    /*) ;;
    *) echo "::error::RUNNER_TEMP must be an absolute directory"; exit 1 ;;
esac
case "$CI_JOB_BASE:$PWD" in
    *','*|*$'\n'*) echo "::error::CI bind paths contain unsupported separators"; exit 1 ;;
esac
case "$CI_JOB_BASE" in
    *':'*) echo "::error::RUNNER_TEMP contains an unsupported bind separator"; exit 1 ;;
esac
case "$PWD" in
    *':'*) echo "::error::checkout path contains an unsupported bind separator"; exit 1 ;;
esac
[ -d "$CI_JOB_BASE" ] && [ -w "$CI_JOB_BASE" ] || {
    echo "::error::RUNNER_TEMP is not an existing writable job directory: $CI_JOB_BASE"
    exit 1
}
CI_AVAILABLE_KB="$(df -Pk "$CI_JOB_BASE" | awk 'NR == 2 {print $4}')"
case "$CI_AVAILABLE_KB" in
    ''|*[!0-9]*) echo "::error::cannot establish free space for job scratch"; exit 1 ;;
esac
[ "$CI_AVAILABLE_KB" -ge 2097152 ] || {
    echo "::error::job scratch needs at least 2 GiB available: $CI_JOB_BASE (${CI_AVAILABLE_KB} KiB free)"
    exit 1
}
CI_JOB_ROOT="$(mktemp -d "$CI_JOB_BASE/scitex-notification-sif.XXXXXXXX")"
export APPTAINER_TMPDIR="$CI_JOB_ROOT/apptainer-tmp"
export APPTAINER_CACHEDIR="$CI_JOB_ROOT/apptainer-cache"
export APPTAINER_CONFIGDIR="$CI_JOB_ROOT/apptainer-config"
mkdir -p "$CI_JOB_ROOT/tmp" "$APPTAINER_TMPDIR" "$APPTAINER_CACHEDIR" "$APPTAINER_CONFIGDIR"
# The inner scripts keep their guarded /tmp lifecycle, now backed by this
# job-owned directory instead of the runner's full root filesystem.
export APPTAINERENV_TMPDIR=/tmp

# Explicit checkout and /tmp binds preserve source identity and scratch even
# when a host profile does not bind /scratch automatically. Arrays retain spaces.
GPFS_PROJECT="/data/gpfs/projects/punim0264"
APPTAINER_ARGV=(exec --pwd "$PWD" --bind "$PWD:$PWD" --bind "$CI_JOB_ROOT/tmp:/tmp")
if [ -d "$GPFS_PROJECT" ]; then
    APPTAINER_ARGV+=(--bind "$GPFS_PROJECT")
    GPFS_STATE="present (punim0264 bound)"
else
    GPFS_STATE="absent (no GPFS bind)"
fi

# Echo the resolved plan: when a run fails on an unfamiliar node, the FIRST
# question is which of the two profiles it took.
echo "exec-in-sif: apptainer=$APPTAINER (via $APPTAINER_FROM)"
echo "exec-in-sif: sif=$SIF"
echo "exec-in-sif: sif_sha256=$ACTUAL_SIF_SHA256 (verified)"
echo "exec-in-sif: $GPFS_PROJECT $GPFS_STATE"
echo "exec-in-sif: job_scratch=$CI_JOB_ROOT (available=${CI_AVAILABLE_KB} KiB)"
echo "exec-in-sif: APPTAINER_TMPDIR=$APPTAINER_TMPDIR"
echo "exec-in-sif: + $APPTAINER ${APPTAINER_ARGV[*]} $SIF bash .github/ci/$INNER $*"

exec "$APPTAINER" "${APPTAINER_ARGV[@]}" "$SIF" bash ".github/ci/$INNER" "$@"
