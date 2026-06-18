#!/usr/bin/env python3
# File: /home/ywatanabe/proj/scitex-notification/tests/test_api.py
"""Tests for the public API of scitex_notification.

Covers:
- alert() returns bool
- available_backends() returns list
- available_backends() contains at least one known backend
- DEFAULT_FALLBACK_ORDER is a list
- __version__ is defined
- All __all__ exports exist on the module
"""

from __future__ import annotations

from datetime import datetime

import pytest

from scitex_notification._backends import BACKENDS
from scitex_notification._backends._types import BaseNotifyBackend, NotifyResult


# ---------------------------------------------------------------------------
# Real probe backends (no mocks): registered into the live BACKENDS registry
# so the public alert()/call() dispatcher is exercised deterministically,
# independent of which real channels happen to be configured on the host.
# ---------------------------------------------------------------------------
class _AvailableProbeBackend(BaseNotifyBackend):
    """A real backend that is available and whose send() always succeeds."""

    name = "api_probe_ok"

    def is_available(self) -> bool:
        return True

    async def send(self, message, title=None, level=None, **kwargs) -> NotifyResult:
        return NotifyResult(
            success=True,
            backend=self.name,
            message=message,
            timestamp=datetime.now().isoformat(),
        )


class _UnavailableProbeBackend(BaseNotifyBackend):
    """A real backend that reports it is not available (is_available -> False)."""

    name = "api_probe_unavailable"

    def is_available(self) -> bool:
        return False

    async def send(self, message, title=None, level=None, **kwargs) -> NotifyResult:
        raise AssertionError("send() must not run for an unavailable backend")


@pytest.fixture
def available_probe():
    """Register an available probe backend; restore the registry on teardown."""
    snapshot = dict(BACKENDS)
    BACKENDS[_AvailableProbeBackend.name] = _AvailableProbeBackend
    try:
        yield _AvailableProbeBackend.name
    finally:
        BACKENDS.clear()
        BACKENDS.update(snapshot)


@pytest.fixture
def twilio_unavailable():
    """Pin the 'twilio' backend (used by call()) to an unavailable probe.

    Makes call()'s fail-loud contract deterministic regardless of whether real
    Twilio credentials are configured on the host running the suite.
    """
    snapshot = dict(BACKENDS)
    BACKENDS["twilio"] = _UnavailableProbeBackend
    try:
        yield
    finally:
        BACKENDS.clear()
        BACKENDS.update(snapshot)


# ---------------------------------------------------------------------------
# test_version_defined
# ---------------------------------------------------------------------------
def test_version_attribute_is_defined():
    # Arrange
    import scitex_notification

    # Act
    has_version = hasattr(scitex_notification, "__version__")

    # Assert
    assert has_version


def test_version_attribute_is_string():
    # Arrange
    import scitex_notification

    # Act
    version = scitex_notification.__version__

    # Assert
    assert isinstance(version, str)


def test_version_attribute_is_non_empty():
    # Arrange
    import scitex_notification

    # Act
    version = scitex_notification.__version__

    # Assert
    assert len(version) > 0


# ---------------------------------------------------------------------------
# test_all_exports
# ---------------------------------------------------------------------------
def test_module_exports_required_public_names():
    # Arrange
    import scitex_notification

    expected = [
        "alert",
        "alert_async",
        "available_backends",
        "call",
        "call_async",
        "sms",
        "sms_async",
        "__version__",
    ]

    # Act
    missing = [name for name in expected if not hasattr(scitex_notification, name)]

    # Assert
    assert missing == []


# ---------------------------------------------------------------------------
# test_default_fallback_order_is_list
# ---------------------------------------------------------------------------
def test_default_fallback_order_is_a_list():
    # Arrange
    from scitex_notification import DEFAULT_FALLBACK_ORDER

    # Act
    order = DEFAULT_FALLBACK_ORDER

    # Assert
    assert isinstance(order, list)


def test_default_fallback_order_is_non_empty():
    # Arrange
    from scitex_notification import DEFAULT_FALLBACK_ORDER

    # Act
    order = DEFAULT_FALLBACK_ORDER

    # Assert
    assert len(order) > 0


def test_default_fallback_order_contains_only_strings():
    # Arrange
    from scitex_notification import DEFAULT_FALLBACK_ORDER

    # Act
    non_string = [item for item in DEFAULT_FALLBACK_ORDER if not isinstance(item, str)]

    # Assert
    assert non_string == []


# ---------------------------------------------------------------------------
# test_available_backends_returns_list
# ---------------------------------------------------------------------------
def test_available_backends_returns_a_list():
    # Arrange
    from scitex_notification import available_backends

    # Act
    result = available_backends()

    # Assert
    assert isinstance(result, list)


def test_available_backends_returns_only_strings():
    # Arrange
    from scitex_notification import available_backends

    # Act
    result = available_backends()
    non_string = [item for item in result if not isinstance(item, str)]

    # Assert
    assert non_string == []


# ---------------------------------------------------------------------------
# test_available_backends_contains_known
# ---------------------------------------------------------------------------
def test_available_backends_returns_only_known_names():
    """Every returned backend name must be from the known set."""
    # Arrange
    from scitex_notification import available_backends

    known = {
        "audio",
        "desktop",
        "email",
        "emacs",
        "matplotlib",
        "playwright",
        "telegram",
        "webhook",
        "twilio",
    }

    # Act
    result = available_backends()
    unknown = [name for name in result if name not in known]

    # Assert
    assert unknown == []


# ---------------------------------------------------------------------------
# test_alert_returns_bool (real registered backend, no mock)
# ---------------------------------------------------------------------------
def test_alert_returns_bool_with_available_backend(available_probe):
    """alert() returns a bool when an explicit, available backend delivers."""
    # Arrange
    import scitex_notification

    # Act
    result = scitex_notification.alert(
        "test message", backend=available_probe, fallback=False
    )

    # Assert
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# test_alert_with_invalid_level_is_coerced_not_raised
# ---------------------------------------------------------------------------
def test_alert_with_invalid_level_returns_bool(available_probe):
    """alert() coerces an invalid level to info and does not raise on it."""
    # Arrange
    import scitex_notification

    # Act
    result = scitex_notification.alert(
        "hi", level="not_a_real_level", backend=available_probe, fallback=False
    )

    # Assert
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# test_call_fails_loud_when_twilio_unavailable
# ---------------------------------------------------------------------------
def test_call_raises_when_twilio_unavailable(twilio_unavailable):
    """call() fails loud (ValueError) when its twilio backend is unavailable.

    call() pins backend='twilio', fallback=False, so an unavailable twilio must
    raise rather than silently returning False (no-silent-fallbacks policy).
    """
    # Arrange
    import scitex_notification

    raised: ValueError | None = None

    # Act
    try:
        scitex_notification.call("test")
    except ValueError as exc:
        raised = exc

    # Assert
    assert raised is not None


def test_sms_returns_a_bool_value():
    """sms() always returns a bool."""
    # Arrange
    import scitex_notification

    # Act
    result = scitex_notification.sms("test")

    # Assert
    assert isinstance(result, bool)


# EOF
