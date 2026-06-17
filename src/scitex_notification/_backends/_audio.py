#!/usr/bin/env python3
# Timestamp: "2026-01-13 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_backends/_audio.py

"""Audio notification backend via TTS."""

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
        # Default backend=None so scitex_audio's fallback chain decides
        # (elevenlabs -> luxtts -> gtts -> pyttsx3, with the operator's
        # SCITEX_AUDIO_DEFAULT_BACKEND honoured and a LOUD spoken notice on
        # any degradation). The old hardcoded "gtts" default pinned every
        # notification to the robotic Google voice (operator 2026-06-17).
        # Pass an explicit backend to override.
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

            # Run TTS in executor to not block
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: _audio_speak(
                    full_message,
                    backend=kwargs.get("tts_backend", self.tts_backend),
                    speed=kwargs.get("speed", self.speed),
                    rate=kwargs.get("rate", self.rate),
                ),
            )

            return NotifyResult(
                success=True,
                backend=self.name,
                message=message,
                timestamp=datetime.now().isoformat(),
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
