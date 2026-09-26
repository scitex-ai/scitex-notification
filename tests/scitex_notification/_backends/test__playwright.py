#!/usr/bin/env python3
"""Tests for scitex_notification._backends._playwright.

The backend renders a browser notification via Playwright — an optional
extra — so the real-collaborator tests are guarded with
``pytest.importorskip("playwright")`` and stay green on minimal installs.
"""

import pytest

from scitex_notification._backends._playwright import PlaywrightBackend
from scitex_notification._backends._types import BaseNotifyBackend


def test_backend_name_is_playwright():
    # Arrange
    backend = PlaywrightBackend()
    # Act
    name = backend.name
    # Assert
    assert name == "playwright"


def test_backend_is_a_notify_backend():
    # Arrange
    backend = PlaywrightBackend()
    # Act
    is_backend = isinstance(backend, BaseNotifyBackend)
    # Assert
    assert is_backend


def test_default_timeout_is_five_seconds():
    # Arrange
    backend = PlaywrightBackend()
    # Act
    timeout = backend.timeout
    # Assert
    assert timeout == 5.0


def test_is_available_true_when_playwright_importable():
    # Arrange
    pytest.importorskip("playwright")
    backend = PlaywrightBackend()
    # Act
    available = backend.is_available()
    # Assert
    assert available is True
