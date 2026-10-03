#!/usr/bin/env python3
"""E2E layer (PS-212): real-subsystem workflows, loopback only, no network.

Drives the public `alert()` API end to end through the matplotlib backend
(offscreen Agg canvas, short timeout): figure render -> NotifyResult ->
True. Gated by `RUN_E2E=1` (skipped by default); the `e2e` marker is
registered in `pyproject.toml`.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_E2E") != "1",
    reason="e2e layer runs only with RUN_E2E=1",
)

# Headless canvas BEFORE pyplot is ever touched: MPLBACKEND is read at
# matplotlib import time, and an autouse fixture would run too late (the
# default TkAgg backend blocks forever waiting for a display).
matplotlib = pytest.importorskip("matplotlib")
try:
    matplotlib.use("Agg")
except ImportError:
    pytest.skip(
        "Agg backend unavailable (an interactive backend is already active)",
        allow_module_level=True,
    )


@pytest.mark.e2e
def test_alert_matplotlib_backend_delivers_headless():
    """`alert(backend='matplotlib')` must render offscreen and return True."""
    # Arrange
    import scitex_notification as stxn

    # Act
    delivered = stxn.alert(
        "e2e probe",
        title="scitex-notification e2e",
        backend="matplotlib",
        timeout=0.5,
    )
    # Assert
    assert delivered is True
