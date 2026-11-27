#!/usr/bin/env python3
# File: src/scitex_notification/_templates.py

"""Message templates: render structured data into a subject/body and validate it.

A template is a pair of callables registered under a name:

* ``render(data: dict) -> (subject, body)``
* ``validate(subject, body, **context)`` — raises :class:`MessageFormatError`
  listing every violation, returns ``None`` when the message is well formed.

:func:`render_template` always validates what it renders, so a template can
never produce a message its own validator rejects. :func:`validate_message`
checks an already-written subject/body (for callers that compose by hand).

A template may also register ``html(subject, body) -> str``, which turns a
valid plain-text message into an HTML alternative part with the same
structure (:func:`render_message_html`).

Built-in template ``notice`` — a short notice a person can act on at a glance::

    Subject: [SciTeX][<agent>] <KIND>: <title>      KIND: NEEDS-YOU|DONE|STOPPED|FYI

    ■ NEEDS YOU
    1. <question, one line>
       A) <option>
       B) <option>
       -> recommend: A
       reply: "1 A"

    2. <question>
       ...

    ■ DONE
      - <outcome, one line, with link>

    ■ RUNNING (no action needed)
      - <item>

    ────────────────────────────────────────
    agent: <name> | host: <host> | card/PR: <ids>

Sections appear in that order and empty ones are omitted. A blank line
separates sections, questions and the footer rule; nothing else is blank.
"""
from __future__ import annotations

from ._notice import (
    NOTICE_KINDS,
    NOTICE_MAX_LINE_CHARS,
    NOTICE_MAX_LINES,
    NOTICE_RULE,
    NOTICE_SECTION_MARK,
    NOTICE_SECTIONS,
    _render_notice,
    _validate_notice,
)
from ._notice_html import _notice_html
from ._template_registry import (
    MessageFormatError,
    list_templates,
    load_message_data,
    register_template,
    render_message_html,
    render_template,
    validate_message,
)

__all__ = [
    "MessageFormatError",
    "NOTICE_KINDS",
    "NOTICE_MAX_LINES",
    "NOTICE_MAX_LINE_CHARS",
    "NOTICE_RULE",
    "NOTICE_SECTIONS",
    "NOTICE_SECTION_MARK",
    "list_templates",
    "load_message_data",
    "register_template",
    "render_message_html",
    "render_template",
    "validate_message",
]

register_template(
    "notice", _render_notice, _validate_notice, html=_notice_html
)

# EOF
