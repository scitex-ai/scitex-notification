#!/usr/bin/env python3
# Timestamp: "2026-03-16 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_cli/__init__.py

"""CLI entry point for scitex-notification."""

from scitex_notification._cli._main import cli as main

__all__ = ["main"]

# EOF


# audit §4 — inject version into root --help
try:
    from importlib.metadata import version as _v
    main.help = (
        f"scitex-notification (v{_v('scitex-notification')}) — "
        + (main.help or "").lstrip()
    )
except Exception:
    pass
