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
# test_alert_returns_bool (real backend, no mock)
# ---------------------------------------------------------------------------
def test_alert_returns_bool_with_default_backend():
    """alert() always returns a bool with the default backend selection."""
    # Arrange
    import scitex_notification

    # Act
    result = scitex_notification.alert(
        "test message", backend="desktop", fallback=False
    )

    # Assert
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# test_alert_with_invalid_level_falls_back_to_info
# ---------------------------------------------------------------------------
def test_alert_with_invalid_level_returns_bool():
    """alert() should not raise on an invalid level string."""
    # Arrange
    import scitex_notification

    # Act
    result = scitex_notification.alert(
        "hi", level="not_a_real_level", backend="desktop", fallback=False
    )

    # Assert
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# test_call_returns_bool
# ---------------------------------------------------------------------------
def test_call_returns_a_bool_value():
    """call() always returns a bool."""
    # Arrange
    import scitex_notification

    # Act
    result = scitex_notification.call("test")

    # Assert
    assert isinstance(result, bool)


def test_sms_returns_a_bool_value():
    """sms() always returns a bool."""
    # Arrange
    import scitex_notification

    # Act
    result = scitex_notification.sms("test")

    # Assert
    assert isinstance(result, bool)


# EOF
