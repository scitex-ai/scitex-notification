#!/usr/bin/env python3
# Timestamp: "2026-03-16 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_mcp/handlers.py

"""MCP handlers for scitex-notification server."""

from __future__ import annotations

import inspect
from datetime import datetime
from typing import Optional

__all__ = [
    "notify_handler",
    "notify_by_level_handler",
    "list_backends_handler",
    "available_backends_handler",
    "get_config_handler",
    "skills_list_handler",
    "skills_get_handler",
]


def _constructor_kwargs(backend_cls: type, kwargs: dict) -> dict:
    """Return only the kwargs that ``backend_cls.__init__`` actually accepts.

    The MCP layer receives every tool argument as one flat mapping, but a
    backend constructor is strict — ``WebhookBackend(url=None)``,
    ``TelegramBackend(bot_token, chat_id)``. Forwarding a send-level argument
    (``idempotency_key``, ``image_path``, ``voice_path``, ``document_path``)
    into construction raises ``TypeError`` BEFORE ``send()`` runs, so the
    notification is never attempted and the caller gets a generic failure with
    no delivery receipt. Send-level arguments belong to ``send()``, which takes
    ``**kwargs``.

    The CLASS signature is inspected, not ``__init__``'s: a backend that
    defines no ``__init__`` of its own inherits ``object.__init__``, whose
    ``(self, /, *args, **kwargs)`` reads as "accepts anything" and leaks every
    send-level argument into ``Backend(idempotency_key=...)`` — the same
    ``TypeError`` this seam exists to prevent, one inheritance level down
    (``DesktopBackend`` is the live case). Inspecting the class resolves
    through the MRO and excludes ``self``, so only a backend that genuinely
    declares ``**kwargs`` receives the whole mapping.
    """
    params = inspect.signature(backend_cls).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return dict(kwargs)
    return {k: v for k, v in kwargs.items() if k in params}


async def notify_handler(
    message: str,
    title: Optional[str] = None,
    level: str = "info",
    backend: Optional[str] = None,
    backends: Optional[list[str]] = None,
    timeout: float = 5.0,
    **kwargs,
) -> dict:
    """Send notification via specified backend(s)."""
    from .._backends import BACKENDS, NotifyLevel, get_backend
    from .._backends._config import get_config

    try:
        # Determine notification level
        try:
            notify_level = NotifyLevel(level.lower())
        except ValueError:
            notify_level = NotifyLevel.INFO

        # Determine backends to use
        config = get_config()
        if backends:
            backend_list = backends
        elif backend:
            backend_list = [backend]
        else:
            backend_list = [config.default_backend]

        results = []
        success_count = 0

        for backend_name in backend_list:
            try:
                if backend_name not in BACKENDS:
                    results.append(
                        {
                            "backend": backend_name,
                            "success": False,
                            "error": f"Unknown backend: {backend_name}",
                        }
                    )
                    continue

                b = get_backend(
                    backend_name,
                    **_constructor_kwargs(BACKENDS[backend_name], kwargs),
                )
                result = await b.send(
                    message,
                    title=title,
                    level=notify_level,
                    timeout=timeout,
                    **kwargs,
                )

                results.append(
                    {
                        "backend": backend_name,
                        "success": result.success,
                        "error": result.error,
                        "error_code": result.error_code,
                        "delivery_id": result.delivery_id,
                        "idempotency_key": result.idempotency_key,
                        "details": result.details,
                    }
                )

                if result.success:
                    success_count += 1

            except Exception as e:
                results.append(
                    {
                        "backend": backend_name,
                        "success": False,
                        "error": str(e),
                    }
                )

        return {
            "success": success_count > 0,
            "message": message,
            "title": title,
            "level": level,
            "backends_used": backend_list,
            "results": results,
            "success_count": success_count,
            "total_count": len(backend_list),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


async def notify_by_level_handler(
    message: str,
    title: Optional[str] = None,
    level: str = "info",
) -> dict:
    """Send notification using backends configured for the level."""
    from .._backends import NotifyLevel
    from .._backends._config import get_config

    try:
        # Determine notification level
        try:
            notify_level = NotifyLevel(level.lower())
        except ValueError:
            notify_level = NotifyLevel.INFO

        # Get backends configured for this level
        config = get_config()
        backend_list = config.get_available_backends_for_level(notify_level)

        if not backend_list:
            backend_list = [config.default_backend]

        # Use notify_handler with determined backends
        return await notify_handler(
            message=message,
            title=title,
            level=level,
            backends=backend_list,
        )

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


async def list_backends_handler() -> dict:
    """List all notification backends with their status."""
    from .._backends import BACKENDS
    from .._backends._config import is_backend_available

    try:
        backends_info = []

        for name, cls in BACKENDS.items():
            try:
                backend = cls()
                is_available = backend.is_available()
                pkg_available = is_backend_available(name)

                backends_info.append(
                    {
                        "name": name,
                        "available": is_available,
                        "package_available": pkg_available,
                        "class": cls.__name__,
                    }
                )
            except Exception as e:
                backends_info.append(
                    {
                        "name": name,
                        "available": False,
                        "error": str(e),
                    }
                )

        return {
            "success": True,
            "backends": backends_info,
            "total_count": len(backends_info),
            "available_count": sum(1 for b in backends_info if b.get("available")),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


async def available_backends_handler() -> dict:
    """Get list of currently available backends."""
    from .._backends import available_backends

    try:
        available = available_backends()

        return {
            "success": True,
            "available_backends": available,
            "count": len(available),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


async def get_config_handler() -> dict:
    """Get current notification configuration."""
    from .._backends._config import UIConfig, get_config

    try:
        # Reset to get fresh config
        UIConfig.reset()
        config = get_config()

        return {
            "success": True,
            "config": {
                "default_backend": config.default_backend,
                "backend_priority": config.backend_priority,
                "available_priority": config.get_available_backend_priority(),
                "first_available": config.get_first_available_backend(),
                "level_backends": {
                    "info": config._config.get("level_backends", {}).get("info", []),
                    "warning": config._config.get("level_backends", {}).get(
                        "warning", []
                    ),
                    "error": config._config.get("level_backends", {}).get("error", []),
                    "critical": config._config.get("level_backends", {}).get(
                        "critical", []
                    ),
                },
                "timeouts": config._config.get("timeouts", {}),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# §5 — skills introspection handlers (per audit-mcp-tools convention)
async def skills_list_handler() -> dict:
    """List the names of every skill page shipped by scitex-notification."""
    from pathlib import Path

    try:
        skills_dir = Path(__file__).parent.parent / "_skills" / "scitex-notification"
        names = sorted(p.stem for p in skills_dir.glob("*.md") if p.name != "SKILL.md")
        return {
            "success": True,
            "package": "scitex-notification",
            "skills": names,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def skills_get_handler(name: str) -> dict:
    """Fetch the full Markdown content of one scitex-notification skill page."""
    from pathlib import Path

    try:
        skills_dir = Path(__file__).parent.parent / "_skills" / "scitex-notification"
        target = skills_dir / f"{name}.md"
        if not target.exists():
            available = sorted(
                p.stem for p in skills_dir.glob("*.md") if p.name != "SKILL.md"
            )
            return {
                "success": False,
                "error": f"unknown skill {name!r}; available: {available}",
            }
        return {
            "success": True,
            "package": "scitex-notification",
            "name": name,
            "content": target.read_text(encoding="utf-8"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# EOF
