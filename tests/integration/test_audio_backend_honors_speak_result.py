#!/usr/bin/env python3
# Timestamp: "2026-06-18 (ywatanabe)"
# File: tests/integration/test_audio_backend_honors_speak_result.py

"""The audio backend must report what ``scitex_audio.speak()`` actually did.

Second half of the operator bug (2026-06-17)
--------------------------------------------
``AudioBackend.send()`` used to call ``scitex_audio.speak(...)`` and ignore
its return value, always reporting ``success=True``. ``speak()`` returns a
dict whose ``played`` / ``success`` keys say whether audio actually reached a
sink — so a degraded ``{"success": False, "played": False}`` (suspended sink,
no network for gtts, ...) was reported as a delivered notification. Combined
with the dispatcher's old auto-fallback, that is exactly how an explicit
``--backend audio`` quietly turned into an emacs popup.

Contract pinned here
--------------------
- ``speak()`` returning ``played=True``  -> ``NotifyResult.success is True``.
- ``speak()`` returning ``played=False`` -> ``NotifyResult.success is False``
  and the result's ``error`` is populated (so the dispatcher / CLI can fail
  loud).
- The backend forwards ``backend=None`` (its new default) to ``speak()`` so
  scitex_audio's own fallback chain + SCITEX_AUDIO_* config decide the voice
  — the same path ``scitex-audio speak-text`` takes — instead of the old
  hardcoded ``gtts``.

No mocks (repo policy): the collaborator is swapped by reassigning the
module-level ``_audio_speak`` to a real, hand-rolled function that records its
call and returns a real dict, then restored on teardown. This is the
documented "look the callable up via the module" injection pattern, not a
mock object.
"""

from __future__ import annotations

import asyncio

import pytest

import scitex_notification._backends._audio as audio_mod
from scitex_notification._backends._audio import AudioBackend


class _RecordingSpeak:
    """A real stand-in for scitex_audio.speak that returns a chosen dict."""

    def __init__(self, result: dict):
        self._result = result
        self.calls: list[dict] = []

    def __call__(self, text, **kwargs):
        self.calls.append({"text": text, **kwargs})
        return dict(self._result)


def _install_speak(monkeyfree_result: dict) -> _RecordingSpeak:
    """Install a recording speak() onto the module; return it for assertions."""
    fake = _RecordingSpeak(monkeyfree_result)
    audio_mod._audio_speak = fake
    audio_mod._AUDIO_AVAILABLE = True
    return fake


@pytest.fixture
def restore_audio_module():
    """Snapshot and restore the audio module's swappable globals."""
    prev_speak = audio_mod._audio_speak
    prev_flag = audio_mod._AUDIO_AVAILABLE
    try:
        yield
    finally:
        audio_mod._audio_speak = prev_speak
        audio_mod._AUDIO_AVAILABLE = prev_flag


@pytest.fixture
def played_result(restore_audio_module):
    """speak() reports audio played; yield the AudioBackend.send() result."""
    _install_speak({"success": True, "played": True, "backend": "elevenlabs"})
    return asyncio.run(AudioBackend().send("played ok"))


@pytest.fixture
def not_played_recorder(restore_audio_module):
    """speak() reports it did NOT play; yield (result, recorder)."""
    fake = _install_speak(
        {"success": False, "played": False, "error": "sink SUSPENDED"}
    )
    result = asyncio.run(AudioBackend().send("did not play"))
    return result, fake


@pytest.fixture
def backend_arg_recorder(restore_audio_module):
    """Capture what backend= the AudioBackend forwards to speak()."""
    fake = _install_speak({"success": True, "played": True})
    asyncio.run(AudioBackend().send("which backend"))
    return fake


def test_send_reports_success_when_speak_played(played_result):
    """played=True from speak() => NotifyResult.success is True."""
    # Arrange
    result = played_result
    # Act
    success = result.success
    # Assert
    assert success is True


def test_send_reports_failure_when_speak_did_not_play(not_played_recorder):
    """played=False from speak() => NotifyResult.success is False (no false ok)."""
    # Arrange
    result, _fake = not_played_recorder
    # Act
    success = result.success
    # Assert
    assert success is False


def test_send_surfaces_speak_error_when_not_played(not_played_recorder):
    """A non-played result carries an error string so callers can fail loud."""
    # Arrange
    result, _fake = not_played_recorder
    # Act
    error = result.error or ""
    # Assert
    assert "SUSPENDED" in error


def test_send_forwards_none_backend_to_speak_by_default(backend_arg_recorder):
    """Default AudioBackend forwards backend=None (scitex_audio chain decides)."""
    # Arrange
    fake = backend_arg_recorder
    # Act
    forwarded_backend = fake.calls[0].get("backend")
    # Assert
    assert forwarded_backend is None


# EOF
