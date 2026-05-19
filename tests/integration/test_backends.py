#!/usr/bin/env python3
# File: /home/ywatanabe/proj/scitex-notification/tests/test_backends.py
"""Tests for the backend registry and backend types.

Covers:
- BACKENDS dict has expected keys
- get_backend() returns a BaseNotifyBackend instance
- get_backend() raises ValueError for unknown name
- All backends have is_available()
- All backends have send()
- NotifyResult dataclass fields
- NotifyLevel enum values
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# test_backends_dict_has_expected_keys
# ---------------------------------------------------------------------------
def test_backends_dict_has_expected_keys():
    # Arrange
    from scitex_notification._backends import BACKENDS

    expected_keys = {
        "audio",
        "email",
        "desktop",
        "emacs",
        "webhook",
        "matplotlib",
        "playwright",
        "telegram",
        "twilio",
    }

    # Act
    actual_keys = set(BACKENDS.keys())

    # Assert
    assert actual_keys == expected_keys


# ---------------------------------------------------------------------------
# test_get_backend_returns_instance
# ---------------------------------------------------------------------------
def test_get_backend_returns_base_instance():
    # Arrange
    from scitex_notification._backends import get_backend
    from scitex_notification._backends._types import BaseNotifyBackend

    # Act
    backend = get_backend("desktop")

    # Assert
    assert isinstance(backend, BaseNotifyBackend)


# ---------------------------------------------------------------------------
# test_get_backend_unknown_raises
# ---------------------------------------------------------------------------
def test_get_backend_unknown_name_raises_value_error():
    # Arrange
    from scitex_notification._backends import get_backend

    # Act / Assert
    # Assert
    with pytest.raises(ValueError, match="Unknown backend"):
        get_backend("nonexistent_backend_xyz")


# ---------------------------------------------------------------------------
# test_all_backends_have_is_available
# ---------------------------------------------------------------------------
def test_all_backends_have_is_available_attribute():
    # Arrange
    from scitex_notification._backends import BACKENDS

    # Act
    missing = [
        name for name, cls in BACKENDS.items() if not hasattr(cls(), "is_available")
    ]

    # Assert
    assert missing == []


def test_all_backends_is_available_is_callable():
    # Arrange
    from scitex_notification._backends import BACKENDS

    # Act
    not_callable = [
        name for name, cls in BACKENDS.items() if not callable(cls().is_available)
    ]

    # Assert
    assert not_callable == []


def test_all_backends_is_available_returns_bool():
    # Arrange
    from scitex_notification._backends import BACKENDS

    # Act
    non_bool = [
        name
        for name, cls in BACKENDS.items()
        if not isinstance(cls().is_available(), bool)
    ]

    # Assert
    assert non_bool == []


# ---------------------------------------------------------------------------
# test_all_backends_have_send_method
# ---------------------------------------------------------------------------
def test_all_backends_have_send_attribute():
    # Arrange
    from scitex_notification._backends import BACKENDS

    # Act
    missing = [name for name, cls in BACKENDS.items() if not hasattr(cls(), "send")]

    # Assert
    assert missing == []


def test_all_backends_send_is_callable():
    # Arrange
    from scitex_notification._backends import BACKENDS

    # Act
    not_callable = [name for name, cls in BACKENDS.items() if not callable(cls().send)]

    # Assert
    assert not_callable == []


def test_all_backends_send_is_coroutine_function():
    # Arrange
    import inspect

    from scitex_notification._backends import BACKENDS

    # Act
    not_coro = [
        name
        for name, cls in BACKENDS.items()
        if not inspect.iscoroutinefunction(cls().send)
    ]

    # Assert
    assert not_coro == []


# ---------------------------------------------------------------------------
# test_notify_result_dataclass
# ---------------------------------------------------------------------------
def test_notify_result_minimal_construction_keeps_success_flag():
    # Arrange
    from scitex_notification._backends._types import NotifyResult

    # Act
    result = NotifyResult(
        success=True,
        backend="desktop",
        message="hello",
        timestamp="2026-01-01T00:00:00",
    )

    # Assert
    assert result.success is True


def test_notify_result_minimal_construction_keeps_backend_name():
    # Arrange
    from scitex_notification._backends._types import NotifyResult

    # Act
    result = NotifyResult(
        success=True,
        backend="desktop",
        message="hello",
        timestamp="2026-01-01T00:00:00",
    )

    # Assert
    assert result.backend == "desktop"


def test_notify_result_minimal_construction_keeps_message():
    # Arrange
    from scitex_notification._backends._types import NotifyResult

    # Act
    result = NotifyResult(
        success=True,
        backend="desktop",
        message="hello",
        timestamp="2026-01-01T00:00:00",
    )

    # Assert
    assert result.message == "hello"


def test_notify_result_minimal_construction_keeps_timestamp():
    # Arrange
    from scitex_notification._backends._types import NotifyResult

    # Act
    result = NotifyResult(
        success=True,
        backend="desktop",
        message="hello",
        timestamp="2026-01-01T00:00:00",
    )

    # Assert
    assert result.timestamp == "2026-01-01T00:00:00"


def test_notify_result_minimal_construction_defaults_error_to_none():
    # Arrange
    from scitex_notification._backends._types import NotifyResult

    # Act
    result = NotifyResult(
        success=True,
        backend="desktop",
        message="hello",
        timestamp="2026-01-01T00:00:00",
    )

    # Assert
    assert result.error is None


def test_notify_result_minimal_construction_defaults_details_to_none():
    # Arrange
    from scitex_notification._backends._types import NotifyResult

    # Act
    result = NotifyResult(
        success=True,
        backend="desktop",
        message="hello",
        timestamp="2026-01-01T00:00:00",
    )

    # Assert
    assert result.details is None


def test_notify_result_with_error_keeps_success_false():
    # Arrange
    from scitex_notification._backends._types import NotifyResult

    # Act
    result = NotifyResult(
        success=False,
        backend="email",
        message="failed",
        timestamp="2026-01-01T00:00:00",
        error="SMTP error",
        details={"code": 500},
    )

    # Assert
    assert result.success is False


def test_notify_result_with_error_keeps_error_string():
    # Arrange
    from scitex_notification._backends._types import NotifyResult

    # Act
    result = NotifyResult(
        success=False,
        backend="email",
        message="failed",
        timestamp="2026-01-01T00:00:00",
        error="SMTP error",
        details={"code": 500},
    )

    # Assert
    assert result.error == "SMTP error"


def test_notify_result_with_error_keeps_details_dict():
    # Arrange
    from scitex_notification._backends._types import NotifyResult

    # Act
    result = NotifyResult(
        success=False,
        backend="email",
        message="failed",
        timestamp="2026-01-01T00:00:00",
        error="SMTP error",
        details={"code": 500},
    )

    # Assert
    assert result.details == {"code": 500}


# ---------------------------------------------------------------------------
# test_notify_level_enum
# ---------------------------------------------------------------------------
def test_notify_level_info_has_value_info():
    # Arrange
    from scitex_notification._backends._types import NotifyLevel

    # Act
    value = NotifyLevel.INFO.value

    # Assert
    assert value == "info"


def test_notify_level_warning_has_value_warning():
    # Arrange
    from scitex_notification._backends._types import NotifyLevel

    # Act
    value = NotifyLevel.WARNING.value

    # Assert
    assert value == "warning"


def test_notify_level_error_has_value_error():
    # Arrange
    from scitex_notification._backends._types import NotifyLevel

    # Act
    value = NotifyLevel.ERROR.value

    # Assert
    assert value == "error"


def test_notify_level_critical_has_value_critical():
    # Arrange
    from scitex_notification._backends._types import NotifyLevel

    # Act
    value = NotifyLevel.CRITICAL.value

    # Assert
    assert value == "critical"


def test_notify_level_from_string_info():
    # Arrange
    from scitex_notification._backends._types import NotifyLevel

    # Act
    level = NotifyLevel("info")

    # Assert
    assert level is NotifyLevel.INFO


def test_notify_level_from_string_warning():
    # Arrange
    from scitex_notification._backends._types import NotifyLevel

    # Act
    level = NotifyLevel("warning")

    # Assert
    assert level is NotifyLevel.WARNING


def test_notify_level_from_string_error():
    # Arrange
    from scitex_notification._backends._types import NotifyLevel

    # Act
    level = NotifyLevel("error")

    # Assert
    assert level is NotifyLevel.ERROR


def test_notify_level_from_string_critical():
    # Arrange
    from scitex_notification._backends._types import NotifyLevel

    # Act
    level = NotifyLevel("critical")

    # Assert
    assert level is NotifyLevel.CRITICAL


def test_notify_level_invalid_string_raises_value_error():
    # Arrange
    from scitex_notification._backends._types import NotifyLevel

    # Act / Assert
    # Assert
    with pytest.raises(ValueError):
        NotifyLevel("not_a_level")


# ---------------------------------------------------------------------------
# test_backend_name_attribute
# ---------------------------------------------------------------------------
def test_all_backends_have_name_attribute():
    # Arrange
    from scitex_notification._backends import BACKENDS

    # Act
    missing = [name for name, cls in BACKENDS.items() if not hasattr(cls(), "name")]

    # Assert
    assert missing == []


def test_all_backends_name_attribute_is_string():
    # Arrange
    from scitex_notification._backends import BACKENDS

    # Act
    non_string = [
        name for name, cls in BACKENDS.items() if not isinstance(cls().name, str)
    ]

    # Assert
    assert non_string == []


# EOF
