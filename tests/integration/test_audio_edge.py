#!/usr/bin/env python3
"""Per-edge integration + degradation tests for the scitex-audio edge.

The edge under test
-------------------
``scitex_notification``'s ``audio`` backend wraps ``scitex_audio`` for TTS.
scitex-audio is an OPTIONAL dependency: when it is installed, the ``audio``
backend is advertised by ``available_backends()`` and ``AudioBackend.send()``
drives ``scitex_audio.speak()``; when it is absent, the backend must degrade
gracefully rather than blowing up the caller with an opaque traceback.

The two test kinds every optional edge should have
--------------------------------------------------
1. INTEGRATION (collaborator PRESENT): exercise the real collaborator and
   assert on the concrete contract it produces. Guard with
   ``pytest.importorskip("scitex_audio")`` so the suite stays green on minimal
   installs instead of erroring.

2. DEGRADATION (collaborator ABSENT): simulate the dependency being missing in
   a hermetic, reversible way (a fixture that snapshots ``sys.modules``,
   shadows ``scitex_audio`` with ``None``, and reloads the backend package),
   then assert the documented, caller-safe contract:

   - ``AudioBackend.is_available()`` returns ``False`` (it cannot speak);
   - the ``audio`` backend is dropped from ``available_backends()`` so the
     fallback chain in ``alert()`` skips straight past it;
   - a *direct* ``AudioBackend.send()`` returns the ``NotifyResult`` sentinel
     with ``success=False`` and an informative ``error`` string instead of
     raising ``ImportError`` into the caller.

Conventions honoured (so this stays a clean template):
  - One assertion per test (TQ007): shared, expensive setup is lifted into a
    fixture; each behaviour gets its own named, single-assert test, so a red
    CI line names exactly what broke.
  - Explicit Arrange / Act / Assert markers in every test (TQ002).
  - No ``monkeypatch`` / ``mocker`` (banned by repo no-mocks policy): the
    scitex-audio-absent fixture hand-swaps ``sys.modules`` and restores the
    exact pre-test table on teardown.

Empirically verified contract (scitex_audio present)
-----------------------------------------------------
With scitex-audio installed (e.g. backends ``['gtts', 'elevenlabs']``):
  - ``AudioBackend().is_available()``  -> ``True``
  - ``"audio" in available_backends()`` -> ``True``
With scitex-audio absent:
  - ``AudioBackend().is_available()``  -> ``False``
  - ``"audio" in available_backends()`` -> ``False``
  - ``AudioBackend().send(...)`` -> ``NotifyResult(success=False, error=...)``
"""

from __future__ import annotations

import asyncio
import importlib
import sys

import pytest

# ===========================================================================
# 1. INTEGRATION  —  scitex_audio PRESENT
# ===========================================================================
scitex_audio = pytest.importorskip("scitex_audio")


@pytest.fixture
def audio_backend_present():
    """A fresh AudioBackend with scitex_audio importable. Yields the backend."""
    from scitex_notification._backends._audio import AudioBackend

    return AudioBackend()


def test_audio_backend_reports_available_when_scitex_audio_present(
    audio_backend_present,
):
    """is_available() is True when scitex_audio exposes at least one backend."""
    # Arrange
    backend = audio_backend_present
    # Act
    available = backend.is_available()
    # Assert
    assert available is True


def test_audio_listed_in_available_backends_when_scitex_audio_present():
    """The registry advertises 'audio' once scitex_audio is importable."""
    # Arrange
    from scitex_notification._backends import available_backends

    # Act
    names = available_backends()
    # Assert
    assert "audio" in names


def test_audio_backend_module_flags_scitex_audio_available():
    """The backend module's optional-import guard resolved to AVAILABLE."""
    # Arrange
    import scitex_notification._backends._audio as audio_mod

    # Act
    flag = audio_mod._AUDIO_AVAILABLE
    # Assert
    assert flag is True


def test_audio_backend_bound_scitex_audio_speak_callable():
    """The backend captured a real callable scitex_audio.speak reference."""
    # Arrange
    import scitex_notification._backends._audio as audio_mod

    # Act
    speak = audio_mod._audio_speak
    # Assert
    assert callable(speak)


def test_scitex_audio_exposes_at_least_one_tts_backend():
    """The collaborator advertises >=1 TTS backend (the is_available premise)."""
    # Arrange
    available = scitex_audio.available_backends()
    # Act
    count = len(available)
    # Assert
    assert count > 0


# ===========================================================================
# 2. DEGRADATION  —  scitex_audio ABSENT
# ===========================================================================
@pytest.fixture
def scitex_audio_absent():
    """Make ``import scitex_audio`` fail for the duration of the test.

    Hermetic and reversible:
      1. snapshot the whole ``sys.modules`` so teardown restores it exactly;
      2. evict ``scitex_audio`` and the ``scitex_notification`` backend stack,
         shadow ``scitex_audio`` with ``None`` so a *fresh* import raises
         ImportError, then reload ``scitex_notification._backends`` so it
         re-runs its optional-import guard under the missing dependency.

    Yields the freshly reloaded backend-registry module.
    """
    import scitex_notification._backends  # noqa: F401  (ensure importable first)

    # 1. Full snapshot for an exact restore.
    snapshot = dict(sys.modules)

    # 2. Evict scitex_audio + the scitex_notification backend stack, then block
    #    scitex_audio so the reloaded backend re-runs its try/except guard.
    def _to_evict(name: str) -> bool:
        return (
            name == "scitex_audio"
            or name.startswith("scitex_audio.")
            or name == "scitex_notification"
            or name.startswith("scitex_notification.")
        )

    for name in [n for n in list(sys.modules) if _to_evict(n)]:
        del sys.modules[name]
    sys.modules["scitex_audio"] = None  # type: ignore[assignment]
    reloaded = importlib.import_module("scitex_notification._backends")

    try:
        yield reloaded
    finally:
        # Restore the exact pre-test module table.
        for name in list(sys.modules):
            if name not in snapshot:
                del sys.modules[name]
        sys.modules.update(snapshot)


def test_scitex_audio_absent_fixture_blocks_the_import(scitex_audio_absent):
    """Sanity: under the fixture, ``import scitex_audio`` really does fail."""
    # Arrange
    _ = scitex_audio_absent
    # Act
    module_name = "scitex_audio"
    # Assert
    with pytest.raises(ImportError):
        importlib.import_module(module_name)


def test_audio_backend_module_flags_unavailable_without_scitex_audio(
    scitex_audio_absent,
):
    """The reloaded backend module's import guard resolved to UNAVAILABLE."""
    # Arrange
    audio_mod = importlib.import_module("scitex_notification._backends._audio")
    # Act
    flag = audio_mod._AUDIO_AVAILABLE
    # Assert
    assert flag is False


def test_audio_backend_reports_unavailable_without_scitex_audio(
    scitex_audio_absent,
):
    """is_available() degrades to False when scitex_audio cannot be imported."""
    # Arrange
    audio_mod = importlib.import_module("scitex_notification._backends._audio")
    # Act
    available = audio_mod.AudioBackend().is_available()
    # Assert
    assert available is False


def test_audio_dropped_from_available_backends_without_scitex_audio(
    scitex_audio_absent,
):
    """The registry stops advertising 'audio' so the fallback chain skips it."""
    # Arrange
    backends_mod = scitex_audio_absent
    # Act
    names = backends_mod.available_backends()
    # Assert
    assert "audio" not in names


@pytest.fixture
def audio_send_result_without_scitex_audio(scitex_audio_absent):
    """Call AudioBackend.send() once with scitex_audio absent; yield the result."""
    audio_mod = importlib.import_module("scitex_notification._backends._audio")
    return asyncio.run(audio_mod.AudioBackend().send("build finished"))


def test_audio_send_returns_failure_sentinel_without_scitex_audio(
    audio_send_result_without_scitex_audio,
):
    """send() degrades to a NotifyResult(success=False) (no opaque crash)."""
    # Arrange
    result = audio_send_result_without_scitex_audio
    # Act
    success = result.success
    # Assert
    assert success is False


def test_audio_send_names_itself_as_the_backend_without_scitex_audio(
    audio_send_result_without_scitex_audio,
):
    """The degraded result still attributes the failure to the audio backend."""
    # Arrange
    result = audio_send_result_without_scitex_audio
    # Act
    backend_name = result.backend
    # Assert
    assert backend_name == "audio"


def test_audio_send_reports_missing_scitex_audio_in_error_without_scitex_audio(
    audio_send_result_without_scitex_audio,
):
    """The error string points at the missing scitex_audio dependency."""
    # Arrange
    result = audio_send_result_without_scitex_audio
    # Act
    error = result.error or ""
    # Assert
    assert "scitex_audio" in error


def test_alert_falls_back_past_audio_to_a_working_backend_without_scitex_audio(
    scitex_audio_absent,
):
    """alert() skips the dead audio backend and succeeds via a fallback backend.

    A throwaway in-memory backend is registered as the fallback target so the
    test asserts the *fallthrough* without touching real notification channels.
    """
    # Arrange
    backends_mod = scitex_audio_absent
    from scitex_notification._backends._types import (
        BaseNotifyBackend,
        NotifyResult,
    )

    class _RecordingBackend(BaseNotifyBackend):
        name = "recording"

        def is_available(self) -> bool:
            return True

        async def send(self, message, title=None, level=None, **kwargs):
            from datetime import datetime

            return NotifyResult(
                success=True,
                backend=self.name,
                message=message,
                timestamp=datetime.now().isoformat(),
            )

    backends_mod.BACKENDS["recording"] = _RecordingBackend
    api = importlib.import_module("scitex_notification")
    # Act
    delivered = api.alert(
        "fallback please",
        backend=["audio", "recording"],
        fallback=False,
    )
    # Assert
    assert delivered is True


# EOF
