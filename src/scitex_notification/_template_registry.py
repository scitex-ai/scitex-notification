#!/usr/bin/env python3
# File: src/scitex_notification/_template_registry.py

"""Template registry: register, render, validate and HTML-render messages.

The public API is re-exported by :mod:`scitex_notification._templates`.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Union


class MessageFormatError(ValueError):
    """A message (or its source data) violates its template's format.

    ``violations`` lists every problem found, so a caller can fix them all at
    once instead of one per attempt.
    """

    def __init__(self, template: str, violations: list[str]):
        self.template = template
        self.violations = list(violations)
        lines = "\n".join(f"  - {v}" for v in self.violations)
        super().__init__(f"message does not follow template {template!r}:\n{lines}")


@dataclass(frozen=True)
class _Template:
    name: str
    render: Callable[[Mapping[str, Any]], tuple[str, str]]
    validate: Callable[..., None]
    html: Optional[Callable[[str, str], str]] = None


_REGISTRY: dict[str, _Template] = {}
_LOCK = threading.Lock()


def register_template(
    name: str,
    render: Callable[[Mapping[str, Any]], tuple[str, str]],
    validate: Callable[..., None],
    *,
    html: Optional[Callable[[str, str], str]] = None,
    replace: bool = False,
) -> None:
    """Register a template under ``name``.

    ``render(data)`` returns ``(subject, body)``; ``validate(subject, body,
    **context)`` raises :class:`MessageFormatError` on any violation.
    ``html(subject, body)``, optional, returns an HTML document with the same
    content, for a ``multipart/alternative`` part; it is only ever called on a
    message that passed ``validate``. An existing name is refused unless
    ``replace=True``.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name or ""):
        raise ValueError("template name must be 1-64 characters of [A-Za-z0-9._-]")
    if not callable(render) or not callable(validate):
        raise TypeError("render and validate must both be callable")
    if html is not None and not callable(html):
        raise TypeError("html must be callable")
    with _LOCK:
        if name in _REGISTRY and not replace:
            raise ValueError(f"template {name!r} is already registered")
        _REGISTRY[name] = _Template(name, render, validate, html)


def list_templates() -> list[str]:
    """Names of every registered template."""
    with _LOCK:
        return sorted(_REGISTRY)


def _get(name: str) -> _Template:
    with _LOCK:
        template = _REGISTRY.get(name)
    if template is None:
        raise KeyError(f"unknown template {name!r}; registered: {list_templates()}")
    return template


def render_template(name: str, data: Mapping[str, Any]) -> tuple[str, str]:
    """Render ``data`` with template ``name`` and validate the result.

    Returns ``(subject, body)``. Raises :class:`MessageFormatError` when the
    data is incomplete or the rendered message breaks the template's rules.
    """
    template = _get(name)
    subject, body = template.render(data)
    template.validate(subject, body, **_render_context(data))
    return subject, body


def validate_message(name: str, subject: str, body: str, **context: Any) -> None:
    """Validate an already-written ``subject``/``body`` against template ``name``.

    ``context`` is passed to the template's validator; for ``notice``,
    ``agent=`` additionally requires the subject and footer to name that
    agent. Raises :class:`MessageFormatError` listing every violation.
    """
    _get(name).validate(subject, body, **context)


def render_message_html(name: str, subject: str, body: str, **context: Any) -> str:
    """HTML alternative of an already-written ``subject``/``body``.

    Validates first (raising :class:`MessageFormatError`), so the HTML part
    can never carry anything the plain-text part would have been refused for.
    Raises :class:`ValueError` when template ``name`` has no HTML renderer.
    """
    template = _get(name)
    if template.html is None:
        raise ValueError(f"template {name!r} has no HTML renderer")
    template.validate(subject, body, **context)
    return template.html(subject, body)


def load_message_data(source: Union[str, Path, Mapping[str, Any]]) -> dict:
    """Load template data from a mapping, a ``.json`` file or a ``.yaml`` file."""
    if isinstance(source, Mapping):
        return dict(source)
    path = Path(source)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "YAML message data needs PyYAML (pip install pyyaml); "
                "or pass the data as JSON"
            ) from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise MessageFormatError("data", [f"{path}: top level must be a mapping"])
    return data


def _render_context(data: Mapping[str, Any]) -> dict:
    meta = data.get("meta") if isinstance(data, Mapping) else None
    agent = meta.get("agent") if isinstance(meta, Mapping) else None
    return {"agent": agent} if agent else {}

# EOF
