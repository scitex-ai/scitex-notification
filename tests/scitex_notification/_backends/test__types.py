#!/usr/bin/env python3
"""Tests for scitex_notification._backends._types core types."""

import pytest

from scitex_notification._backends._types import (
    BaseNotifyBackend,
    NotifyLevel,
    NotifyResult,
)


class TestNotifyLevel:
    def test_has_exactly_four_levels(self):
        # Arrange
        expected = {"info", "warning", "error", "critical"}

        # Act
        observed = {l.value for l in NotifyLevel}

        # Assert
        assert observed == expected

    def test_info_value_matches_string_info(self):
        # Arrange
        level = NotifyLevel.INFO

        # Act
        value = level.value

        # Assert
        assert value == "info"

    def test_critical_value_matches_string_critical(self):
        # Arrange
        level = NotifyLevel.CRITICAL

        # Act
        value = level.value

        # Assert
        assert value == "critical"


class TestNotifyResult:
    def test_minimal_construction_keeps_success_true(self):
        # Arrange
        kwargs = dict(
            success=True,
            backend="audio",
            message="hi",
            timestamp="2026-05-01T00:00:00",
        )

        # Act
        result = NotifyResult(**kwargs)

        # Assert
        assert result.success is True

    def test_minimal_construction_keeps_backend_name(self):
        # Arrange
        kwargs = dict(
            success=True,
            backend="audio",
            message="hi",
            timestamp="2026-05-01T00:00:00",
        )

        # Act
        result = NotifyResult(**kwargs)

        # Assert
        assert result.backend == "audio"

    def test_minimal_construction_defaults_error_to_none(self):
        # Arrange
        kwargs = dict(
            success=True,
            backend="audio",
            message="hi",
            timestamp="2026-05-01T00:00:00",
        )

        # Act
        result = NotifyResult(**kwargs)

        # Assert
        assert result.error is None

    def test_minimal_construction_defaults_details_to_none(self):
        # Arrange
        kwargs = dict(
            success=True,
            backend="audio",
            message="hi",
            timestamp="2026-05-01T00:00:00",
        )

        # Act
        result = NotifyResult(**kwargs)

        # Assert
        assert result.details is None

    def test_with_error_keeps_success_false(self):
        # Arrange
        kwargs = dict(
            success=False,
            backend="email",
            message="x",
            timestamp="2026-05-01T00:00:00",
            error="SMTP down",
        )

        # Act
        result = NotifyResult(**kwargs)

        # Assert
        assert result.success is False

    def test_with_error_keeps_error_string(self):
        # Arrange
        kwargs = dict(
            success=False,
            backend="email",
            message="x",
            timestamp="2026-05-01T00:00:00",
            error="SMTP down",
        )

        # Act
        result = NotifyResult(**kwargs)

        # Assert
        assert result.error == "SMTP down"


class TestBaseNotifyBackend:
    def test_abstract_class_cannot_be_instantiated(self):
        # Arrange
        target_cls = BaseNotifyBackend

        # Act / Assert
        # Assert
        with pytest.raises(TypeError, match="abstract"):
            target_cls()

    def test_concrete_subclass_is_available_returns_true(self):
        # Arrange
        class Dummy(BaseNotifyBackend):
            name = "dummy"

            async def send(self, message, title=None, level=NotifyLevel.INFO, **kw):
                return NotifyResult(True, "dummy", message, "now")

            def is_available(self):
                return True

        # Act
        instance = Dummy()
        availability = instance.is_available()

        # Assert
        assert availability is True

    def test_concrete_subclass_keeps_name_attribute(self):
        # Arrange
        class Dummy(BaseNotifyBackend):
            name = "dummy"

            async def send(self, message, title=None, level=NotifyLevel.INFO, **kw):
                return NotifyResult(True, "dummy", message, "now")

            def is_available(self):
                return True

        # Act
        instance = Dummy()
        observed_name = instance.name

        # Assert
        assert observed_name == "dummy"


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])

# EOF
