"""The audio backend must NOT pin to gtts by default (operator 2026-06-17).

Defaulting backend=None defers to scitex_audio's fallback chain (elevenlabs
-> luxtts -> gtts -> pyttsx3, honouring SCITEX_AUDIO_DEFAULT_BACKEND, loud on
degradation) instead of the robotic Google voice. AAA markers; one assert.
"""

from __future__ import annotations

from scitex_notification._backends._audio import AudioBackend


def test_default_backend_is_none_not_gtts():
    # Arrange
    backend = AudioBackend()
    # Act
    chosen = backend.tts_backend
    # Assert
    assert chosen is None


def test_explicit_backend_is_honoured():
    # Arrange
    backend = AudioBackend(backend="elevenlabs")
    # Act
    chosen = backend.tts_backend
    # Assert
    assert chosen == "elevenlabs"
