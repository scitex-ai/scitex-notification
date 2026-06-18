#!/usr/bin/env python3
# Timestamp: "2026-03-16 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/__init__.py

"""SciTeX Notification Module - User alerts and feedback.

Usage:
    import scitex_notification as stxn

    # Simple alert - uses fallback priority (audio -> emacs -> desktop -> ...)
    stxn.alert("2FA required!")

    # Specify backend (no fallback)
    stxn.alert("Error", backend="email")

    # Multiple backends (tries all)
    stxn.alert("Critical", backend=["audio", "email"])

    # Use fallback explicitly
    stxn.alert("Important", fallback=True)

    # Make a phone call via Twilio
    stxn.call("Critical alert!")

    # Send an SMS via Twilio
    stxn.sms("Build done!")

Environment Variables:
    SCITEX_NOTIFICATION_DEFAULT_BACKEND: audio, email, desktop, webhook
    SCITEX_NOTIFICATION_ENV_SRC: path to .env file to auto-load on import
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional, Union

from ._env_loader import load_scitex_notification_env as _load_env

_load_env()

from ._backends import NotifyLevel as _AlertLevel
from ._backends import available_backends as _available_backends
from ._backends import get_backend as _get_backend
from ._notify_legacy import notify, send_gmail

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _v

    try:
        __version__ = _v("scitex-notification")
    except PackageNotFoundError:
        __version__ = "0.0.0+local"
    del _v, PackageNotFoundError
except ImportError:  # pragma: no cover — only on ancient Pythons
    __version__ = "0.0.0+local"
__all__ = [
    "alert",
    "alert_async",
    "available_backends",
    "call",
    "call_async",
    "notify",
    "send_gmail",
    "sms",
    "sms_async",
    "__version__",
]

# Default fallback priority order
DEFAULT_FALLBACK_ORDER = [
    "audio",  # 1st: TTS audio (non-blocking, immediate)
    "emacs",  # 2nd: Emacs minibuffer (if in Emacs)
    "matplotlib",  # 3rd: Visual popup
    "playwright",  # 4th: Browser popup
    "email",  # 5th: Email (slowest, most reliable)
]


def available_backends() -> list[str]:
    """Return list of available alert backends."""
    return _available_backends()


async def alert_async(
    message: str,
    title: Optional[str] = None,
    backend: Optional[Union[str, list[str]]] = None,
    level: str = "info",
    fallback: Optional[bool] = None,
    **kwargs,
) -> bool:
    """Send alert asynchronously.

    Parameters
    ----------
    message : str
        Alert message
    title : str, optional
        Alert title
    backend : str or list[str], optional
        Backend(s) to use. If None, walks the default fallback priority order.
        If a single backend name is given, ONLY that backend is used (no
        silent substitution) unless ``fallback=True`` is passed explicitly.
    level : str
        Alert level: info, warning, error, critical
    fallback : bool, optional
        Controls whether other backends are tried after the requested one(s).
        If left as ``None`` (default), it resolves to ``backend is None`` —
        i.e. an EXPLICIT backend request fails loud rather than silently
        falling through to another channel (no-silent-fallbacks policy). Pass
        ``True`` to opt back into fallback for an explicit backend, or
        ``False`` to forbid it even when ``backend is None``.

    Returns
    -------
    bool
        True if the requested backend(s) delivered the alert.

    Raises
    ------
    ValueError
        If a single explicit backend is requested with fallback disabled and
        that backend is not currently available — the caller asked for a
        specific channel that cannot fire, so we fail loud instead of
        returning a quiet ``False`` that looks like a transient send failure.
    """
    try:
        lvl = _AlertLevel(level.lower())
    except ValueError:
        lvl = _AlertLevel.INFO

    # Resolve the fallback default: an explicit backend must not silently
    # substitute. Only auto-fall-through when no backend was named.
    if fallback is None:
        fallback = backend is None

    # Determine backends to try
    if backend is None:
        # No backend specified: use fallback priority
        default = os.getenv("SCITEX_NOTIFICATION_DEFAULT_BACKEND", "audio")
        if fallback:
            # Start with default, then try others in priority order
            backends = [default] + [b for b in DEFAULT_FALLBACK_ORDER if b != default]
        else:
            backends = [default]
    else:
        # Backend specified: use exactly it. Append fallbacks ONLY if the
        # caller explicitly opted in via fallback=True.
        backends = [backend] if isinstance(backend, str) else list(backend)
        if fallback and len(backends) == 1:
            # Add fallback backends after the specified one
            backends = backends + [
                b for b in DEFAULT_FALLBACK_ORDER if b not in backends
            ]

    # Fail loud: a single explicit backend with no fallback that isn't
    # available is a request we cannot honour. Don't pretend it was a normal
    # send failure (which the caller might retry) — say what's wrong.
    available = _available_backends()
    explicit_single = backend is not None and not fallback and len(backends) == 1
    if explicit_single and backends[0] not in available:
        raise ValueError(
            f"Notification backend {backends[0]!r} was requested but is not "
            f"available. Available backends: {available or '(none)'}. "
            f"Install/configure it, or omit --backend to use the fallback "
            f"chain."
        )

    # Try backends until one succeeds.
    last_error: Optional[str] = None
    for name in backends:
        if name not in available:
            continue
        try:
            b = _get_backend(name)
            result = await b.send(message, title=title, level=lvl, **kwargs)
            if result.success:
                return True
            last_error = result.error or last_error
        except Exception as e:
            last_error = str(e)

    # Fail loud for the explicit single-backend case: the one channel the
    # caller demanded tried and failed — surface its error rather than a
    # silent False.
    if explicit_single and last_error:
        raise RuntimeError(f"Notification backend {backends[0]!r} failed: {last_error}")

    return False


def alert(
    message: str,
    title: Optional[str] = None,
    backend: Optional[Union[str, list[str]]] = None,
    level: str = "info",
    fallback: Optional[bool] = None,
    **kwargs,
) -> bool:
    """Send alert synchronously.

    Parameters
    ----------
    message : str
        Alert message
    title : str, optional
        Alert title
    backend : str or list[str], optional
        Backend(s) to use. If None, walks the fallback priority order. A
        single explicit backend is used on its own (no silent substitution)
        unless ``fallback=True`` is passed.
    level : str
        Alert level: info, warning, error, critical
    fallback : bool, optional
        If None (default) resolves to ``backend is None`` — an explicit
        backend never silently falls back. See :func:`alert_async`.

    Returns
    -------
    bool
        True if the requested backend(s) delivered the alert.

    Raises
    ------
    ValueError / RuntimeError
        When a single explicit backend (fallback disabled) is unavailable or
        fails — see :func:`alert_async`. The fallback path (``backend=None``)
        still returns ``False`` on total failure.

    Fallback Order
    --------------
    1. audio      - TTS (fast, non-blocking)
    2. emacs      - Minibuffer message
    3. matplotlib - Visual popup
    4. playwright - Browser popup
    5. email      - Email (slowest)
    """
    try:
        asyncio.get_running_loop()
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                alert_async(message, title, backend, level, fallback, **kwargs),
            )
            return future.result(timeout=30)
    except RuntimeError:
        return asyncio.run(
            alert_async(message, title, backend, level, fallback, **kwargs)
        )


def call(
    message: str,
    title: Optional[str] = None,
    level: str = "info",
    to_number: Optional[str] = None,
    **kwargs,
) -> bool:
    """Make a phone call via Twilio.

    Convenience wrapper for alert(backend="twilio").
    """
    return alert(
        message,
        title=title,
        backend="twilio",
        level=level,
        fallback=False,
        to_number=to_number,
        **kwargs,
    )


async def call_async(
    message: str,
    title: Optional[str] = None,
    level: str = "info",
    to_number: Optional[str] = None,
    **kwargs,
) -> bool:
    """Make a phone call via Twilio (async)."""
    return await alert_async(
        message,
        title=title,
        backend="twilio",
        level=level,
        fallback=False,
        to_number=to_number,
        **kwargs,
    )


async def sms_async(
    message: str,
    title: Optional[str] = None,
    to_number: Optional[str] = None,
    **kwargs,
) -> bool:
    """Send an SMS via Twilio (async).

    Parameters
    ----------
    message : str
        SMS body text
    title : str, optional
        Prepended to message if provided
    to_number : str, optional
        Override SCITEX_NOTIFICATION_TWILIO_TO

    Returns
    -------
    bool
        True if SMS sent successfully
    """
    from ._backends._twilio import send_sms as _send_sms

    result = await _send_sms(
        message,
        title=title,
        to_number=to_number,
        **kwargs,
    )
    return result.success


def sms(
    message: str,
    title: Optional[str] = None,
    to_number: Optional[str] = None,
    **kwargs,
) -> bool:
    """Send an SMS via Twilio.

    Parameters
    ----------
    message : str
        SMS body text
    title : str, optional
        Prepended to message if provided
    to_number : str, optional
        Override SCITEX_NOTIFICATION_TWILIO_TO

    Returns
    -------
    bool
        True if SMS sent successfully
    """
    try:
        asyncio.get_running_loop()
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                sms_async(message, title, to_number, **kwargs),
            )
            return future.result(timeout=30)
    except RuntimeError:
        return asyncio.run(sms_async(message, title, to_number, **kwargs))


# Apply @supports_return_as decorator if scitex_dev is available
try:
    from scitex_dev.decorators import supports_return_as as _supports_return_as

    alert = _supports_return_as(alert)
    call = _supports_return_as(call)
    sms = _supports_return_as(sms)
except ImportError:
    pass


# EOF
