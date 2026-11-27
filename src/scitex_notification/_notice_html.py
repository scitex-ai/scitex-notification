#!/usr/bin/env python3
# File: src/scitex_notification/_notice_html.py

"""HTML alternative of a valid ``notice``: same structure, real headings and lists."""

from __future__ import annotations

import html as _html

from ._notice import _URL, NOTICE_SECTIONS, _parse_notice

def _inline(text: str) -> str:
    """Escape ``text`` for HTML and link its http(s) URLs."""
    escaped = _html.escape(text, quote=True)
    return _URL.sub(lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>', escaped)


def _notice_html(subject: str, body: str) -> str:
    notice, _ = _parse_notice(subject, body, None)
    out = [
        "<!DOCTYPE html>",
        '<html><head><meta charset="utf-8">'
        f"<title>{_html.escape(subject)}</title></head>",
        '<body style="font-family: sans-serif; font-size: 14px; line-height: 1.5;">',
    ]
    for index, items in notice.sections:
        out.append(
            '<h3 style="margin: 1.2em 0 0.4em; border-bottom: 1px solid #999;">'
            f"{_html.escape(NOTICE_SECTIONS[index])}</h3>"
        )
        if index == 0:
            out.append("<ol>")
            for question in items:
                options = "".join(
                    f"<li><b>{letter})</b> {_inline(text)}</li>"
                    for letter, text in question.options
                )
                reply = question.reply or ("", "")
                out.append(
                    f'<li value="{question.number}" style="margin-bottom: 0.8em;">'
                    f"{_inline(question.text)}"
                    f'<ul style="list-style: none; padding-left: 1em;">{options}</ul>'
                    f"recommend: <b>{_html.escape(question.recommend or '')}</b>"
                    f" &nbsp; reply: <code>{reply[0]} {_html.escape(reply[1])}</code>"
                    "</li>"
                )
            out.append("</ol>")
        else:
            out.append("<ul>")
            out += [f"<li>{_inline(item)}</li>" for item in items]
            out.append("</ul>")
    out += [
        "<hr>",
        f'<p style="color: #666; font-size: 12px;">{_inline(notice.footer or "")}</p>',
        "</body></html>",
    ]
    return "\n".join(out) + "\n"

# EOF
