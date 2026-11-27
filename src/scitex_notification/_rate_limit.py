#!/usr/bin/env python3
# File: src/scitex_notification/_rate_limit.py

"""Repeat suppression / rate limiting per key per time window.

State is one small JSON file per key under a directory, guarded by
``flock``, so separate processes (cron jobs, agents, alarm scripts) on the
same host share it safely. The mailbox or any remote service is never
consulted.

Default state directory: ``$SCITEX_NOTIFICATION_RATE_LIMIT_DIR``, else
``$SCITEX_DIR/notification/runtime/rate-limit`` (``SCITEX_DIR`` defaults to
``~/.scitex``).
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Iterator, Optional, Union

__all__ = ["RateLimiter", "default_rate_limit_dir"]


def default_rate_limit_dir() -> Path:
    explicit = os.environ.get("SCITEX_NOTIFICATION_RATE_LIMIT_DIR")
    if explicit:
        return Path(explicit).expanduser()
    root = Path(os.environ.get("SCITEX_DIR", str(Path.home() / ".scitex")))
    return root.expanduser() / "notification/runtime/rate-limit"


class RateLimiter:
    """Allow at most ``max_events`` per ``key`` within any ``window_s`` seconds.

    >>> limiter = RateLimiter(3600)
    >>> limiter.allow("disk-full:/data")   # True: first time, recorded
    >>> limiter.allow("disk-full:/data")   # False: suppressed for an hour

    ``allow`` checks and records atomically. ``peek`` checks without
    recording (for dry runs). :meth:`hold` records only when the guarded
    block completes, so a failed send does not suppress its retry.
    """

    def __init__(
        self,
        window_s: float,
        state_dir: Optional[Union[str, Path]] = None,
        *,
        max_events: int = 1,
    ):
        if not window_s or window_s <= 0:
            raise ValueError("window_s must be a positive number of seconds")
        if max_events < 1:
            raise ValueError("max_events must be at least 1")
        self.window_s = float(window_s)
        self.max_events = int(max_events)
        self.state_dir = (
            Path(state_dir).expanduser() if state_dir else default_rate_limit_dir()
        )

    def _path(self, key: str) -> Path:
        if not isinstance(key, str) or not key:
            raise ValueError("rate-limit key must be a non-empty string")
        return self.state_dir / (
            hashlib.sha256(key.encode()).hexdigest()[:32] + ".json"
        )

    def _recent(self, path: Path, now: float) -> tuple[list[float], int]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return [], 0
        events = [
            float(t) for t in data.get("events", []) if now - float(t) < self.window_s
        ]
        return events, int(data.get("suppressed", 0))

    def _write(
        self, path: Path, key: str, events: list[float], suppressed: int
    ) -> None:
        temp = path.with_suffix(".tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump({"key": key, "events": events, "suppressed": suppressed}, stream)
        os.replace(temp, path)

    @contextlib.contextmanager
    def _locked(self, key: str) -> Iterator[Path]:
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self._path(key)
        with open(path.with_suffix(".lock"), "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield path
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def peek(self, key: str, now: Optional[float] = None) -> bool:
        """Would ``allow(key)`` return True now? Records nothing."""
        now = time.time() if now is None else now
        with self._locked(key) as path:
            events, _ = self._recent(path, now)
        return len(events) < self.max_events

    def allow(self, key: str, now: Optional[float] = None) -> bool:
        """Return True and record the event, or False (and count a suppression)."""
        with self.hold(key, now) as allowed:
            pass
        return allowed

    @contextlib.contextmanager
    def hold(self, key: str, now: Optional[float] = None) -> Iterator[bool]:
        """Lock ``key``; yield whether an event is allowed; record it on success.

        The event is recorded only if the ``with`` block exits without an
        exception, and other processes wait on the same key meanwhile, so
        "check, send, record" is one atomic step.
        """
        now = time.time() if now is None else now
        with self._locked(key) as path:
            events, suppressed = self._recent(path, now)
            allowed = len(events) < self.max_events
            if not allowed:
                self._write(path, key, events, suppressed + 1)
                yield False
                return
            yield True
            self._write(path, key, events + [now], 0)

    def suppressed_count(self, key: str) -> int:
        """Events suppressed for ``key`` since its last allowed event."""
        with self._locked(key) as path:
            return self._recent(path, time.time())[1]


# EOF
