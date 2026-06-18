#!/usr/bin/env python3
# Timestamp: "2026-06-18 (ywatanabe)"
# File: tests/integration/test_explicit_backend_no_silent_fallback.py

"""Regression tests: an EXPLICIT backend must never silently substitute.

The operator bug (2026-06-17)
-----------------------------
``scitex-notification send --backend audio hello`` showed an EMACS visual
notification, not audio. Root cause: ``alert()`` defaulted ``fallback=True``
and, for an explicit single backend, appended the whole fallback chain
(``audio -> emacs -> matplotlib -> playwright -> email``). So whenever the
audio backend reported failure (e.g. a SUSPENDED PulseAudio sink, or gtts
with no network), the dispatcher silently dropped to emacs and reported
success. That violates the ecosystem's "no silent fallbacks / fail loud"
rule.

The fixed contract (this file pins it)
--------------------------------------
- ``alert(msg, backend=X)`` with ``fallback`` left unset uses ONLY ``X``.
- If ``X`` is unavailable  -> ``ValueError`` (loud, actionable).
- If ``X`` is available but its ``send()`` fails -> ``RuntimeError`` carrying
  the backend's own error string.
- A second backend (e.g. emacs) is NEVER tried for an explicit request unless
  the caller opts in with ``fallback=True``.
- ``alert(msg)`` (no backend) keeps walking the fallback chain and returns a
  plain ``bool`` — the bare-default path is unchanged.

No mocks (repo policy): every collaborator here is a real, hand-rolled
``BaseNotifyBackend`` subclass registered into the real ``BACKENDS`` registry
via a snapshot/restore fixture, so the tests exercise the real dispatcher.
"""

from __future__ import annotations

from datetime import datetime

import pytest

import scitex_notification as notif
from scitex_notification._backends import BACKENDS
from scitex_notification._backends._types import BaseNotifyBackend, NotifyResult


class _UnavailableBackend(BaseNotifyBackend):
    """A real backend that is never available (is_available -> False)."""

    name = "unavailable_probe"

    def is_available(self) -> bool:
        return False

    async def send(self, message, title=None, level=None, **kwargs) -> NotifyResult:
        raise AssertionError("send() must not run for an unavailable backend")


class _FailingBackend(BaseNotifyBackend):
    """Available, but every send() reports failure with an error string."""

    name = "failing_probe"

    def is_available(self) -> bool:
        return True

    async def send(self, message, title=None, level=None, **kwargs) -> NotifyResult:
        return NotifyResult(
            success=False,
            backend=self.name,
            message=message,
            timestamp=datetime.now().isoformat(),
            error="sink suspended",
        )


class _RecordingBackend(BaseNotifyBackend):
    """Available and always succeeds; records that it was used."""

    name = "recording_probe"
    used = False

    def is_available(self) -> bool:
        return True

    async def send(self, message, title=None, level=None, **kwargs) -> NotifyResult:
        type(self).used = True
        return NotifyResult(
            success=True,
            backend=self.name,
            message=message,
            timestamp=datetime.now().isoformat(),
        )


@pytest.fixture
def registered_probes():
    """Register the probe backends in the real registry; restore on teardown."""
    snapshot = dict(BACKENDS)
    _RecordingBackend.used = False
    BACKENDS["unavailable_probe"] = _UnavailableBackend
    BACKENDS["failing_probe"] = _FailingBackend
    BACKENDS["recording_probe"] = _RecordingBackend
    try:
        yield
    finally:
        BACKENDS.clear()
        BACKENDS.update(snapshot)


@pytest.fixture
def unavailable_backend_error(registered_probes):
    """Call alert() on an unavailable explicit backend; yield the raised error."""
    with pytest.raises((ValueError, RuntimeError)) as excinfo:
        notif.alert("fail loud please", backend="unavailable_probe")
    return excinfo.value


@pytest.fixture
def failing_backend_error(registered_probes):
    """Call alert() on an available-but-failing backend; yield the raised error."""
    with pytest.raises((ValueError, RuntimeError)) as excinfo:
        notif.alert("no silent emacs", backend="failing_probe")
    return excinfo.value


def test_explicit_unavailable_backend_raises_value_error(unavailable_backend_error):
    """An explicit unavailable backend fails with a ValueError, not via emacs."""
    # Arrange
    error = unavailable_backend_error
    # Act
    is_value_error = isinstance(error, ValueError)
    # Assert
    assert is_value_error is True


def test_explicit_unavailable_backend_error_names_the_backend(
    unavailable_backend_error,
):
    """The raised error names the requested backend so the fix is obvious."""
    # Arrange
    error = unavailable_backend_error
    # Act
    message = str(error)
    # Assert
    assert "unavailable_probe" in message


def test_explicit_failing_backend_raises_runtime_error(failing_backend_error):
    """An explicit backend whose send() fails raises rather than substituting."""
    # Arrange
    error = failing_backend_error
    # Act
    is_runtime_error = isinstance(error, RuntimeError)
    # Assert
    assert is_runtime_error is True


def test_explicit_failing_backend_error_carries_backend_message(failing_backend_error):
    """The raised error surfaces the backend's own error string."""
    # Arrange
    error = failing_backend_error
    # Act
    message = str(error)
    # Assert
    assert "sink suspended" in message


def test_explicit_failing_backend_does_not_fall_through(failing_backend_error):
    """A working backend listed elsewhere is NOT used for an explicit request."""
    # Arrange
    _ = failing_backend_error  # the alert() call already happened in the fixture
    # Act
    fell_through = _RecordingBackend.used
    # Assert
    assert fell_through is False


def test_explicit_backend_with_optin_fallback_uses_next_backend(registered_probes):
    """fallback=True lets an explicit backend fall through to a working one."""
    # Arrange
    _RecordingBackend.used = False
    # Act
    delivered = notif.alert(
        "opt in",
        backend=["failing_probe", "recording_probe"],
        fallback=True,
    )
    # Assert
    assert delivered is True


def test_explicit_available_backend_that_succeeds_returns_true(registered_probes):
    """An explicit, available, working backend delivers and returns True."""
    # Arrange
    message = "delivered"
    # Act
    delivered = notif.alert(message, backend="recording_probe")
    # Assert
    assert delivered is True


@pytest.fixture
def bare_default_unavailable_result(registered_probes):
    """Run the bare (no-backend) path with the default pinned to unavailable.

    Forces ``SCITEX_NOTIFICATION_DEFAULT_BACKEND`` to a backend that is not
    available so nothing fires, exercising the bare path without touching a
    real channel. Yields the returned value (must be a plain bool, no raise).
    """
    import os

    prev = os.environ.get("SCITEX_NOTIFICATION_DEFAULT_BACKEND")
    os.environ["SCITEX_NOTIFICATION_DEFAULT_BACKEND"] = "unavailable_probe"
    try:
        result = notif.alert("bare", fallback=False)
    finally:
        if prev is None:
            os.environ.pop("SCITEX_NOTIFICATION_DEFAULT_BACKEND", None)
        else:
            os.environ["SCITEX_NOTIFICATION_DEFAULT_BACKEND"] = prev
    return result


def test_bare_default_path_returns_false_without_raising(
    bare_default_unavailable_result,
):
    """The bare path returns False (not the explicit-backend loud error)."""
    # Arrange
    result = bare_default_unavailable_result
    # Act
    is_plain_false = result is False
    # Assert
    assert is_plain_false is True


# EOF
