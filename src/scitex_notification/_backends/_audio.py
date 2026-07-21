#!/usr/bin/env python3
# Timestamp: "2026-06-18 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_backends/_audio.py

"""Audio notification backend via TTS.

This backend is a thin, honest wrapper over ``scitex_audio.speak`` — the
exact same call path as ``scitex-audio speak-text``. It does NOT re-implement
any audio routing of its own; it lets ``scitex_audio`` pick the TTS backend
(elevenlabs -> luxtts -> gtts -> pyttsx3) and resolve local/relay mode, then
faithfully reports whether audio actually played.

Fail loud, no silent success: ``speak()`` returns a dict whose ``success`` /
``played`` keys say whether audio reached a sink. The old implementation
ignored that dict and always reported ``success=True``, so a degraded
``{"success": False, "played": False}`` (e.g. a SUSPENDED PulseAudio sink)
looked like a delivered notification and the dispatcher's fallback chain never
got a chance to try another channel. We now propagate the real outcome.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from ._types import BaseNotifyBackend, NotifyLevel, NotifyResult

try:
    from scitex_audio import available_backends as _audio_available_backends
    from scitex_audio import speak as _audio_speak

    _AUDIO_AVAILABLE = True
except ImportError:
    _AUDIO_AVAILABLE = False
    _audio_speak = None
    _audio_available_backends = None


class AudioBackend(BaseNotifyBackend):
    """Audio notification via scitex_audio TTS."""

    name = "audio"

    def __init__(
        self,
        backend: Optional[str] = None,
        speed: float = 1.5,
        rate: int = 180,
    ):
        # backend=None (default) lets scitex_audio's own fallback chain decide
        # (elevenlabs -> luxtts -> gtts -> pyttsx3), honouring the operator's
        # SCITEX_AUDIO_* config — the same path ``scitex-audio speak-text``
        # takes. The old hardcoded "gtts" default pinned every notification to
        # the robotic Google voice AND required internet, so an offline box
        # silently dropped to emacs (operator 2026-06-17). Pass an explicit
        # backend to override.
        self.tts_backend = backend
        self.speed = speed
        self.rate = rate

    def is_available(self) -> bool:
        if not _AUDIO_AVAILABLE:
            return False
        try:
            return len(_audio_available_backends()) > 0
        except Exception:
            return False

    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        level: NotifyLevel = NotifyLevel.INFO,
        **kwargs,
    ) -> NotifyResult:
        try:
            if not _AUDIO_AVAILABLE or _audio_speak is None:
                raise ImportError(
                    "scitex_audio is not installed. "
                    "Install it with: pip install scitex-audio"
                )

            # Prepend title if provided
            full_message = f"{title}. {message}" if title else message

            # Add urgency prefix for critical/error levels
            if level == NotifyLevel.CRITICAL:
                full_message = f"Critical alert! {full_message}"
            elif level == NotifyLevel.ERROR:
                full_message = f"Error. {full_message}"

            tts_backend = kwargs.get("tts_backend", self.tts_backend)

            # Run TTS in executor to not block the event loop. Capture the
            # result dict so we can report whether audio actually played.
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: _audio_speak(
                    full_message,
                    backend=tts_backend,
                    speed=kwargs.get("speed", self.speed),
                    rate=kwargs.get("rate", self.rate),
                ),
            )

            # scitex_audio.speak() returns a dict; trust it instead of
            # assuming success. ``played`` is the strongest signal (audio
            # reached a sink); fall back to ``success`` for paths that don't
            # set ``played`` (e.g. play=False, which we never request here).
            result = result if isinstance(result, dict) else {}
            played = result.get("played")
            ok = bool(played) if played is not None else bool(result.get("success"))

            if not ok:
                err = result.get("error") or (
                    f"scitex_audio.speak() did not play audio (result={result!r})"
                )
                return NotifyResult(
                    success=False,
                    backend=self.name,
                    message=message,
                    timestamp=datetime.now().isoformat(),
                    error=str(err),
                    details=result or None,
                )

            return NotifyResult(
                success=True,
                backend=self.name,
                message=message,
                timestamp=datetime.now().isoformat(),
                details=result or None,
            )
        except Exception as e:
            return NotifyResult(
                success=False,
                backend=self.name,
                message=message,
                timestamp=datetime.now().isoformat(),
                error=str(e),
            )


# EOF
