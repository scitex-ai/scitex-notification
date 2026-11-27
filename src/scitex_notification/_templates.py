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

Built-in template ``notice`` — a short notice a person can act on at a glance::

    Subject: [SciTeX][<agent>] <KIND>: <title>      KIND: NEEDS-YOU|DONE|STOPPED|FYI

    NEEDS YOU
    1. <question, one line>
       A) <option>  B) <option>  -> recommend: A
       reply: "1 A"
    DONE
    - <outcome, one line, with link>
    RUNNING (no action needed)
    - <item>
    --
    agent: <name> | host: <host> | card/PR: <ids>

Sections appear in that order and empty ones are omitted.
"""

from __future__ import annotations

import json
import re
import string
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Union

__all__ = [
    "MessageFormatError",
    "NOTICE_KINDS",
    "NOTICE_MAX_LINES",
    "NOTICE_MAX_LINE_CHARS",
    "NOTICE_SECTIONS",
    "list_templates",
    "load_message_data",
    "register_template",
    "render_template",
    "validate_message",
]


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


_REGISTRY: dict[str, _Template] = {}
_LOCK = threading.Lock()


def register_template(
    name: str,
    render: Callable[[Mapping[str, Any]], tuple[str, str]],
    validate: Callable[..., None],
    *,
    replace: bool = False,
) -> None:
    """Register a template under ``name``.

    ``render(data)`` returns ``(subject, body)``; ``validate(subject, body,
    **context)`` raises :class:`MessageFormatError` on any violation. An
    existing name is refused unless ``replace=True``.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name or ""):
        raise ValueError("template name must be 1-64 characters of [A-Za-z0-9._-]")
    if not callable(render) or not callable(validate):
        raise TypeError("render and validate must both be callable")
    with _LOCK:
        if name in _REGISTRY and not replace:
            raise ValueError(f"template {name!r} is already registered")
        _REGISTRY[name] = _Template(name, render, validate)


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


# ----------------------------------------------------------------- notice ---

NOTICE_KINDS = ("NEEDS-YOU", "DONE", "STOPPED", "FYI")
NOTICE_SECTIONS = ("NEEDS YOU", "DONE", "RUNNING (no action needed)")
#: Most non-empty lines a notice may have, headers and footer included.
NOTICE_MAX_LINES = 20
#: Longest single line; an item is one line, not a paragraph.
NOTICE_MAX_LINE_CHARS = 200

_NAME = r"[A-Za-z0-9._@:-]{1,128}"
_SUBJECT = re.compile(rf"^\[SciTeX\]\[({_NAME})\] ([A-Z-]+): (\S.*)$")
_FOOTER = re.compile(rf"^agent: ({_NAME}) \| host: (\S+) \| card/PR: (\S.*)$")
_QUESTION = re.compile(r"^(\d+)\. \S")
_OPTIONS = re.compile(r"^ {3}([A-Z]\) .*?)\s+-> recommend: ([A-Z])\s*$")
_REPLY = re.compile(r'^ {3}reply: "(\d+) ([A-Z])"$')
# Shapes of credentials that must never be mailed (best-effort, deterministic).
_SECRET = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}"
    r"|\bsk-[A-Za-z0-9_-]{20,}"
    r"|\bxox[abposr]-[A-Za-z0-9-]{10,}"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S+)",
    re.I,
)


def _one_line(value: Any, where: str, problems: list[str]) -> str:
    text = "" if value is None else str(value)
    if not text.strip():
        problems.append(f"{where} is empty")
    elif "\n" in text or "\r" in text:
        problems.append(f"{where} must be a single line")
    return " ".join(text.split())


def _render_notice(data: Mapping[str, Any]) -> tuple[str, str]:
    problems: list[str] = []
    if not isinstance(data, Mapping):
        raise MessageFormatError("notice", ["data must be a mapping"])
    kind = str(data.get("kind", "")).strip().upper()
    if kind not in NOTICE_KINDS:
        problems.append(f"kind must be one of {', '.join(NOTICE_KINDS)}")
    title = _one_line(data.get("title"), "title", problems)
    meta = data.get("meta") or {}
    if not isinstance(meta, Mapping):
        problems.append("meta must be a mapping")
        meta = {}
    agent = _one_line(meta.get("agent"), "meta.agent", problems)
    host = _one_line(meta.get("host"), "meta.host", problems)
    refs = meta.get("refs")
    if isinstance(refs, (list, tuple)):
        refs = ", ".join(str(r) for r in refs)
    refs = " ".join(str(refs or "-").split())

    lines: list[str] = []
    questions = data.get("questions") or []
    if questions:
        lines.append(NOTICE_SECTIONS[0])
    letters = string.ascii_uppercase
    for number, question in enumerate(questions, 1):
        where = f"questions[{number - 1}]"
        if not isinstance(question, Mapping):
            problems.append(f"{where} must be a mapping")
            continue
        text = _one_line(question.get("text"), f"{where}.text", problems)
        options = [str(o) for o in (question.get("options") or [])]
        if not 2 <= len(options) <= len(letters):
            problems.append(f"{where}.options needs at least two choices")
            options = options or ["?"]
        recommend = str(question.get("recommend", "")).strip()
        labels = letters[: len(options)]
        if recommend in options and recommend not in labels:
            recommend = labels[options.index(recommend)]
        if recommend not in labels:
            problems.append(
                f"{where}.recommend must be an option letter ({', '.join(labels)})"
                " or one of the option texts"
            )
            recommend = "?"
        choices = "  ".join(
            f"{label}) {_one_line(o, f'{where}.options', problems)}"
            for label, o in zip(labels, options)
        )
        lines += [
            f"{number}. {text}",
            f"   {choices}  -> recommend: {recommend}",
            f'   reply: "{number} {recommend}"',
        ]
    for section, key in ((NOTICE_SECTIONS[1], "done"), (NOTICE_SECTIONS[2], "running")):
        items = data.get(key) or []
        if isinstance(items, str):
            items = [items]
        if items:
            lines.append(section)
            lines += [
                f"- {_one_line(item, f'{key}[{i}]', problems)}"
                for i, item in enumerate(items)
            ]
    lines += ["--", f"agent: {agent} | host: {host} | card/PR: {refs}"]
    if problems:
        raise MessageFormatError("notice", problems)
    return f"[SciTeX][{agent}] {kind}: {title}", "\n".join(lines) + "\n"


def _validate_notice(subject: str, body: str, *, agent: Optional[str] = None) -> None:
    problems: list[str] = []
    subject = subject or ""
    match = _SUBJECT.match(subject) if "\n" not in subject else None
    kind = subject_agent = None
    if not match:
        problems.append(
            "subject must be '[SciTeX][<agent>] <KIND>: <one line>' on one line"
        )
    else:
        subject_agent, kind = match.group(1), match.group(2)
        if kind not in NOTICE_KINDS:
            problems.append(
                f"subject KIND {kind!r} must be one of {', '.join(NOTICE_KINDS)}"
            )
        if agent and subject_agent != agent:
            problems.append(
                f"subject names agent {subject_agent!r}, expected {agent!r}"
            )

    lines = [line.rstrip() for line in (body or "").splitlines() if line.strip()]
    if not lines:
        raise MessageFormatError("notice", problems + ["body is empty"])
    if len(lines) > NOTICE_MAX_LINES:
        problems.append(
            f"body has {len(lines)} non-empty lines; at most {NOTICE_MAX_LINES}"
        )
    for number, line in enumerate(lines, 1):
        if len(line) > NOTICE_MAX_LINE_CHARS:
            problems.append(
                f"line {number} is {len(line)} characters; at most "
                f"{NOTICE_MAX_LINE_CHARS} (one line per item)"
            )
        if _SECRET.search(line):
            problems.append(f"line {number} looks like it contains a credential")

    # Footer: the last two non-empty lines.
    footer_agent = None
    if len(lines) >= 2 and lines[-2] == "--" and _FOOTER.match(lines[-1]):
        footer_agent = _FOOTER.match(lines[-1]).group(1)
        content = lines[:-2]
    else:
        problems.append(
            "footer missing: end with '--' then "
            "'agent: <name> | host: <host> | card/PR: <ids>'"
        )
        content = lines[:-2] if "--" in lines[-2:] else lines
    if footer_agent and subject_agent and footer_agent != subject_agent:
        problems.append(
            f"footer agent {footer_agent!r} differs from subject agent {subject_agent!r}"
        )
    if "--" in content:
        problems.append("'--' may only appear once, directly before the footer")

    # Sections: known headers, in order, first line is a header.
    if content and content[0] not in NOTICE_SECTIONS:
        problems.append(
            f"first line must be a section header ({' / '.join(NOTICE_SECTIONS)}),"
            f" got {content[0]!r}"
        )
    seen: list[int] = []
    section = None
    questions: list[dict] = []
    for line in content:
        if line in NOTICE_SECTIONS:
            index = NOTICE_SECTIONS.index(line)
            if seen and index <= seen[-1]:
                problems.append(
                    f"section {line!r} is out of order or repeated; "
                    f"order is {' / '.join(NOTICE_SECTIONS)}"
                )
            seen.append(index)
            section = index
            continue
        if section is None:
            continue
        if section == 0:
            question = _QUESTION.match(line)
            if question:
                questions.append(
                    {"number": int(question.group(1)), "options": None, "reply": None}
                )
            elif not questions:
                problems.append(f"NEEDS YOU line {line!r} must start with '1. '")
            elif _OPTIONS.match(line):
                listed, recommend = _OPTIONS.match(line).groups()
                labels = re.findall(r"(?:^|\s)([A-Z])\) ", listed)
                if recommend not in labels:
                    problems.append(
                        f"question {questions[-1]['number']} recommends {recommend!r},"
                        f" which is not one of its options ({', '.join(labels)})"
                    )
                questions[-1]["options"] = recommend
            elif _REPLY.match(line):
                questions[-1]["reply"] = _REPLY.match(line).groups()
            else:
                problems.append(
                    f"NEEDS YOU line {line!r} is not a question, an options line "
                    "('   A) ...  B) ...  -> recommend: A') or a reply line "
                    "('   reply: \"1 A\"')"
                )
        elif not line.startswith("- "):
            problems.append(
                f"{NOTICE_SECTIONS[section]} item {line!r} must be one '- ' line"
            )
    for expected, question in enumerate(questions, 1):
        label = f"question {question['number']}"
        if question["number"] != expected:
            problems.append(f"{label} should be numbered {expected}")
        if question["options"] is None:
            problems.append(f"{label} has no options line with '-> recommend: X'")
        reply = question["reply"]
        if reply is None:
            problems.append(f"{label} has no reply line ('   reply: \"N X\"')")
        elif int(reply[0]) != question["number"]:
            problems.append(f"{label} reply line names question {reply[0]}")
    if kind == "NEEDS-YOU" and not any(q["options"] for q in questions):
        problems.append(
            "NEEDS-YOU notice needs a NEEDS YOU section with at least one numbered "
            "question and '-> recommend:'"
        )
    if kind and kind != "NEEDS-YOU" and 0 in seen:
        problems.append("a NEEDS YOU section requires the subject KIND NEEDS-YOU")
    if problems:
        raise MessageFormatError("notice", problems)


register_template("notice", _render_notice, _validate_notice)

# EOF
