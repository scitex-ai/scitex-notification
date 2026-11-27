#!/usr/bin/env python3
# File: src/scitex_notification/_notice.py

"""The built-in ``notice`` template: render, parse and validate.

The layout is documented in :mod:`scitex_notification._templates`.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from ._template_registry import MessageFormatError

# ----------------------------------------------------------------- notice ---

NOTICE_KINDS = ("NEEDS-YOU", "DONE", "STOPPED", "FYI")
NOTICE_SECTIONS = ("NEEDS YOU", "DONE", "RUNNING (no action needed)")
#: Marker that starts every section header line: ``■ NEEDS YOU``.
NOTICE_SECTION_MARK = "■"
#: The rule printed between the content and the footer.
NOTICE_RULE = "─" * 40
#: Most content lines a notice may have: questions, options, recommendation
#: and reply lines, and bullets. Blank lines, section headers, the rule and
#: the footer are layout, not content, and are not counted.
NOTICE_MAX_LINES = 40
#: Longest single line; an item is one line, not a paragraph.
NOTICE_MAX_LINE_CHARS = 200

_HEADERS = tuple(f"{NOTICE_SECTION_MARK} {name}" for name in NOTICE_SECTIONS)
_NAME = r"[A-Za-z0-9._@:-]{1,128}"
_SUBJECT = re.compile(rf"^\[SciTeX\]\[({_NAME})\] ([A-Z-]+): (\S.*)$")
_FOOTER = re.compile(rf"^agent: ({_NAME}) \| host: (\S+) \| card/PR: (\S.*)$")
# A hand-typed rule may use '─' or '-'; 10 to 80 of the same character.
_RULE = re.compile(r"^(?:─{10,80}|-{10,80})$")
_QUESTION = re.compile(r"^(\d+)\. (\S.*)$")
_OPTION = re.compile(r"^ {3}([A-Z])\) (\S.*)$")
_RECOMMEND = re.compile(r"^ {3}-> recommend: ([A-Z])$")
_REPLY = re.compile(r'^ {3}reply: "(\d+) ([A-Z])"$')
_BULLET = re.compile(r"^ {2}- (\S.*)$")
_URL = re.compile(r"https?://[^\s<>\"']+")
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

    blocks: list[list[str]] = []  # joined by one blank line
    questions = data.get("questions") or []
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
        block = [f"{number}. {text}"]
        block += [
            f"   {label}) {_one_line(o, f'{where}.options', problems)}"
            for label, o in zip(labels, options)
        ]
        block += [f"   -> recommend: {recommend}", f'   reply: "{number} {recommend}"']
        if not blocks:
            block.insert(0, _HEADERS[0])
        blocks.append(block)
    for header, key in ((_HEADERS[1], "done"), (_HEADERS[2], "running")):
        items = data.get(key) or []
        if isinstance(items, str):
            items = [items]
        if items:
            blocks.append(
                [header]
                + [
                    f"  - {_one_line(item, f'{key}[{i}]', problems)}"
                    for i, item in enumerate(items)
                ]
            )
    blocks.append([NOTICE_RULE, f"agent: {agent} | host: {host} | card/PR: {refs}"])
    if problems:
        raise MessageFormatError("notice", problems)
    body = "\n\n".join("\n".join(block) for block in blocks) + "\n"
    return f"[SciTeX][{agent}] {kind}: {title}", body


@dataclass
class _Question:
    number: int
    text: str
    options: list = field(default_factory=list)  # [(letter, text)]
    recommend: Optional[str] = None
    reply: Optional[tuple] = None


@dataclass
class _Notice:
    kind: Optional[str] = None
    subject_agent: Optional[str] = None
    sections: list = field(default_factory=list)  # [(index, [_Question] | [str])]
    footer: Optional[str] = None
    questions: list = field(default_factory=list)
    content_lines: int = 0


def _check_subject(subject: str, agent: Optional[str], notice: _Notice, problems):
    match = _SUBJECT.match(subject) if "\n" not in subject else None
    if not match:
        problems.append(
            "subject must be '[SciTeX][<agent>] <KIND>: <one line>' on one line"
        )
        return
    notice.subject_agent, notice.kind = match.group(1), match.group(2)
    if notice.kind not in NOTICE_KINDS:
        problems.append(
            f"subject KIND {notice.kind!r} must be one of {', '.join(NOTICE_KINDS)}"
        )
    if agent and notice.subject_agent != agent:
        problems.append(
            f"subject names agent {notice.subject_agent!r}, expected {agent!r}"
        )


def _check_lines(lines: list[str], problems: list[str]) -> None:
    for number, line in enumerate(lines, 1):
        if len(line) > NOTICE_MAX_LINE_CHARS:
            problems.append(
                f"line {number} is {len(line)} characters; at most "
                f"{NOTICE_MAX_LINE_CHARS} (one line per item)"
            )
        if _SECRET.search(line):
            problems.append(f"line {number} looks like it contains a credential")
        if "\t" in line:
            problems.append(f"line {number} contains a tab; indent with spaces")


def _split_footer(lines: list[str], notice: _Notice, problems) -> list[str]:
    """Take the rule + footer off the end; return the content lines before it."""
    if not (len(lines) >= 2 and _RULE.match(lines[-2]) and _FOOTER.match(lines[-1])):
        problems.append(
            f"footer missing: end with a rule line ({NOTICE_RULE[:10]}...) then "
            "'agent: <name> | host: <host> | card/PR: <ids>'"
        )
        return lines
    notice.footer = lines[-1]
    footer_agent = _FOOTER.match(notice.footer).group(1)
    if notice.subject_agent and footer_agent != notice.subject_agent:
        problems.append(
            f"footer agent {footer_agent!r} differs from subject agent "
            f"{notice.subject_agent!r}"
        )
    content = lines[:-2]
    if not content or content[-1]:
        problems.append("put one blank line before the footer rule")
    while content and not content[-1]:
        content.pop()
    return content


def _misplaced(line: str, problems: list[str]) -> bool:
    """Report a rule or a 0.2.x-style header/separator in the content."""
    if _RULE.match(line):
        problems.append("the rule may only appear once, directly before the footer")
    elif line.strip() in NOTICE_SECTIONS:
        name = line.strip()
        problems.append(
            f"section header {name!r} must be '{NOTICE_SECTION_MARK} {name}' "
            f"(section headers are '{NOTICE_SECTION_MARK} <NAME>')"
        )
    elif line.strip(" -") == "":
        problems.append(
            f"{line!r} is not a rule; the footer rule is one line of 10-80 '─' "
            "(or '-') directly before the footer"
        )
    else:
        return False
    return True


def _question_line(line, blank_before, items, notice, problems) -> None:
    """One line inside NEEDS YOU: a question, or part of the current one."""
    question = _QUESTION.match(line)
    if question:
        if items and not blank_before:
            problems.append(f"put one blank line before question {question.group(1)}")
        elif not items and blank_before:
            problems.append("no blank line between a header and its first item")
        items.append(_Question(int(question.group(1)), question.group(2)))
        notice.questions.append(items[-1])
        return
    if blank_before:
        problems.append(f"no blank line inside a question block ({line!r})")
    if not items:
        problems.append(f"NEEDS YOU line {line!r} must start with '1. '")
        return
    current = items[-1]
    label = f"question {current.number}"
    option, recommend, reply = (
        _OPTION.match(line),
        _RECOMMEND.match(line),
        _REPLY.match(line),
    )
    if option:
        expected = string.ascii_uppercase[len(current.options)]
        if current.recommend or current.reply:
            problems.append(f"{label}: options come before '-> recommend:' and 'reply:'")
        elif option.group(1) != expected:
            problems.append(
                f"{label}: option {option.group(1)!r} should be {expected!r} "
                "(A, B, C, ... in order)"
            )
        current.options.append(option.groups())
    elif recommend:
        if current.recommend or current.reply:
            problems.append(f"{label}: one '-> recommend:' line, before 'reply:'")
        current.recommend = recommend.group(1)
    elif reply:
        if current.reply:
            problems.append(f"{label}: one 'reply:' line")
        current.reply = (int(reply.group(1)), reply.group(2))
    else:
        problems.append(
            f"NEEDS YOU line {line!r} is not a question ('1. ...'), an option "
            "('   A) ...'), a recommendation ('   -> recommend: A') or a reply "
            "line ('   reply: \"1 A\"')"
        )


def _bullet_line(line, blank_before, index, items, problems) -> None:
    if blank_before:
        problems.append(f"no blank line between bullets ({line!r})")
    bullet = _BULLET.match(line)
    if bullet:
        items.append(bullet.group(1))
    else:
        problems.append(
            f"{NOTICE_SECTIONS[index]} item {line!r} must be one '  - ' line "
            "(two spaces, dash, space)"
        )


def _parse_sections(content: list[str], notice: _Notice, problems) -> None:
    if content and content[0] not in _HEADERS:
        problems.append(
            f"first line must be a section header ({' / '.join(_HEADERS)}),"
            f" got {content[0]!r}"
        )
    previous = None  # the previous line; "" when it was blank
    for line in content:
        if not line:
            if previous == "":
                problems.append("only one blank line at a time")
            previous = ""
            continue
        blank_before, previous = previous == "", line
        if line in _HEADERS:
            index = _HEADERS.index(line)
            if notice.sections and index <= notice.sections[-1][0]:
                problems.append(
                    f"section {line!r} is out of order or repeated; "
                    f"order is {' / '.join(_HEADERS)}"
                )
            if notice.sections and not blank_before:
                problems.append(f"put one blank line before section {line!r}")
            notice.sections.append((index, []))
            continue
        if _misplaced(line, problems) or not notice.sections:
            continue
        notice.content_lines += 1
        index, items = notice.sections[-1]
        if index == 0:
            _question_line(line, blank_before, items, notice, problems)
        else:
            _bullet_line(line, blank_before, index, items, problems)


def _check_questions(notice: _Notice, problems: list[str]) -> None:
    for expected, question in enumerate(notice.questions, 1):
        label = f"question {question.number}"
        letters = [letter for letter, _ in question.options]
        if question.number != expected:
            problems.append(f"{label} should be numbered {expected}")
        if len(letters) < 2:
            problems.append(f"{label} needs at least two options ('   A) ...')")
        if question.recommend is None:
            problems.append(f"{label} has no '   -> recommend: X' line")
        elif letters and question.recommend not in letters:
            problems.append(
                f"{label} recommends {question.recommend!r}, which is not one of "
                f"its options ({', '.join(letters)})"
            )
        if question.reply is None:
            problems.append(f"{label} has no reply line ('   reply: \"N X\"')")
            continue
        if question.reply[0] != question.number:
            problems.append(f"{label} reply line names question {question.reply[0]}")
        if question.recommend and question.reply[1] != question.recommend:
            problems.append(
                f"{label} reply line should accept the recommendation "
                f"({question.recommend})"
            )
    has_needs_you = any(index == 0 for index, _ in notice.sections)
    if notice.kind == "NEEDS-YOU" and not any(q.recommend for q in notice.questions):
        problems.append(
            "NEEDS-YOU notice needs a NEEDS YOU section with at least one numbered "
            "question and '-> recommend:'"
        )
    if notice.kind and notice.kind != "NEEDS-YOU" and has_needs_you:
        problems.append("a NEEDS YOU section requires the subject KIND NEEDS-YOU")


def _parse_notice(subject: str, body: str, agent: Optional[str]) -> tuple:
    """Parse a notice into its structure and every way it breaks the layout."""
    problems: list[str] = []
    notice = _Notice()
    _check_subject(subject or "", agent, notice, problems)
    lines = [line.rstrip() for line in (body or "").splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        raise MessageFormatError("notice", problems + ["body is empty"])
    _check_lines(lines, problems)
    _parse_sections(_split_footer(lines, notice, problems), notice, problems)
    if notice.content_lines > NOTICE_MAX_LINES:
        problems.append(
            f"body has {notice.content_lines} content lines; at most "
            f"{NOTICE_MAX_LINES} (blank lines, headers, the rule and the footer "
            "are not counted)"
        )
    _check_questions(notice, problems)
    return notice, problems


def _validate_notice(subject: str, body: str, *, agent: Optional[str] = None) -> None:
    _, problems = _parse_notice(subject, body, agent)
    if problems:
        raise MessageFormatError("notice", problems)


# EOF
