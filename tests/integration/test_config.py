#!/usr/bin/env python3
# File: /home/ywatanabe/proj/scitex-notification/tests/test_config.py
"""Tests for the notification configuration module.

Covers:
- SCITEX_NOTIFICATION_DEFAULT_BACKEND env var
- Default config values when no env vars are set
- UIConfig singleton and reset
- get_config() helper
"""

from __future__ import annotations

import os
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONFIG_ENV_VARS = [
    "SCITEX_NOTIFICATION_DEFAULT_BACKEND",
    "SCITEX_NOTIFICATION_BACKEND_PRIORITY",
]


@contextmanager
def _scoped_env(overrides: dict[str, str | None]):
    """Set/remove env vars and restore originals on exit.

    A value of None removes the variable for the duration of the context.
    Real os.environ mutation — no mock library involved.
    """
    saved: dict[str, str | None] = {}
    try:
        for key in _CONFIG_ENV_VARS:
            saved[key] = os.environ.get(key)
            os.environ.pop(key, None)
        for key, value in overrides.items():
            saved.setdefault(key, os.environ.get(key))
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, prior in saved.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior


# ---------------------------------------------------------------------------
# test_env_var_default_backend
# ---------------------------------------------------------------------------
def test_env_var_sets_default_backend_to_email():
    """SCITEX_NOTIFICATION_DEFAULT_BACKEND should set default_backend."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({"SCITEX_NOTIFICATION_DEFAULT_BACKEND": "email"}):
        UIConfig.reset()
        cfg = UIConfig()
        observed = cfg.default_backend
        UIConfig.reset()

    # Assert
    assert observed == "email"


# ---------------------------------------------------------------------------
# test_default_config_values
# ---------------------------------------------------------------------------
def test_default_config_uses_audio_backend_when_no_env_vars():
    """When no env vars are set, default backend should be 'audio'."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        observed = cfg.default_backend
        UIConfig.reset()

    # Assert
    assert observed == "audio"


def test_default_backend_priority_is_a_list():
    """backend_priority is a list type when no env vars are set."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        observed = cfg.backend_priority
        UIConfig.reset()

    # Assert
    assert isinstance(observed, list)


def test_default_backend_priority_is_non_empty():
    """backend_priority is non-empty when no env vars are set."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        observed_len = len(cfg.backend_priority)
        UIConfig.reset()

    # Assert
    assert observed_len > 0


# ---------------------------------------------------------------------------
# test_backend_priority_from_env
# ---------------------------------------------------------------------------
def test_backend_priority_env_var_sets_priority_order():
    """SCITEX_NOTIFICATION_BACKEND_PRIORITY sets priority order."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({"SCITEX_NOTIFICATION_BACKEND_PRIORITY": "email,desktop,audio"}):
        UIConfig.reset()
        cfg = UIConfig()
        observed = cfg.backend_priority
        UIConfig.reset()

    # Assert
    assert observed == ["email", "desktop", "audio"]


# ---------------------------------------------------------------------------
# test_get_config_returns_ui_config
# ---------------------------------------------------------------------------
def test_get_config_returns_a_ui_config_instance():
    """get_config() should return a UIConfig instance."""
    # Arrange
    from scitex_notification._backends._config import UIConfig, get_config

    # Act
    UIConfig.reset()
    cfg = get_config()
    UIConfig.reset()

    # Assert
    assert isinstance(cfg, UIConfig)


# ---------------------------------------------------------------------------
# test_get_timeout_returns_float
# ---------------------------------------------------------------------------
def test_get_timeout_returns_a_float_value():
    """get_timeout() should return a float for known backends."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        timeout = cfg.get_timeout("matplotlib")
        UIConfig.reset()

    # Assert
    assert isinstance(timeout, float)


def test_get_timeout_returns_a_positive_value():
    """get_timeout() should return a positive number for known backends."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        timeout = cfg.get_timeout("matplotlib")
        UIConfig.reset()

    # Assert
    assert timeout > 0


# ---------------------------------------------------------------------------
# test_get_backends_for_level
# ---------------------------------------------------------------------------
def test_get_backends_for_level_returns_a_list():
    """get_backends_for_level() returns a list of backend names."""
    # Arrange
    from scitex_notification._backends._config import UIConfig
    from scitex_notification._backends._types import NotifyLevel

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        backends = cfg.get_backends_for_level(NotifyLevel.INFO)
        UIConfig.reset()

    # Assert
    assert isinstance(backends, list)


def test_get_backends_for_level_returns_non_empty_list():
    """get_backends_for_level() returns at least one backend."""
    # Arrange
    from scitex_notification._backends._config import UIConfig
    from scitex_notification._backends._types import NotifyLevel

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        backends = cfg.get_backends_for_level(NotifyLevel.INFO)
        UIConfig.reset()

    # Assert
    assert len(backends) > 0


# ---------------------------------------------------------------------------
# test_get_first_available_backend
# ---------------------------------------------------------------------------
def test_get_first_available_backend_returns_string():
    """get_first_available_backend() returns a string."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        first = cfg.get_first_available_backend()
        UIConfig.reset()

    # Assert
    assert isinstance(first, str)


def test_get_first_available_backend_returns_non_empty_string():
    """get_first_available_backend() returns a non-empty string."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        first = cfg.get_first_available_backend()
        UIConfig.reset()

    # Assert
    assert len(first) > 0


# ---------------------------------------------------------------------------
# test_reload_does_not_raise
# ---------------------------------------------------------------------------
def test_reload_runs_without_raising():
    """reload() should complete without raising."""
    # Arrange
    from scitex_notification._backends._config import UIConfig

    # Act
    with _scoped_env({}):
        UIConfig.reset()
        cfg = UIConfig()
        cfg.reload()
        # If we got here without an exception, the test passes.
        completed = True
        UIConfig.reset()

    # Assert
    assert completed is True


# EOF
