"""Tests for message templates: the built-in ``notice`` and the registry."""

import json

import pytest

from scitex_notification import (
    MessageFormatError,
    list_templates,
    load_message_data,
    register_template,
    render_message_html,
    render_template,
    validate_message,
)
from scitex_notification._templates import NOTICE_MAX_LINES, NOTICE_RULE

SUBJECT = "[SciTeX][worker-1] NEEDS-YOU: storage quota decision"
BODY = f"""\
■ NEEDS YOU
1. Raise the archive quota to 2 TB?
   A) yes
   B) no, prune old runs
   -> recommend: A
   reply: "1 A"

■ DONE
  - nightly backup verified https://example.org/run/42

■ RUNNING (no action needed)
  - re-index of the archive

{NOTICE_RULE}
agent: worker-1 | host: compute-01 | card/PR: card-7, #12
"""
FOOTER = f"\n{NOTICE_RULE}\nagent: worker-1 | host: h | card/PR: -\n"

DATA = {
    "kind": "needs-you",
    "title": "storage quota decision",
    "questions": [
        {
            "text": "Raise the archive quota to 2 TB?",
            "options": ["yes", "no, prune old runs"],
            "recommend": "A",
        }
    ],
    "done": ["nightly backup verified https://example.org/run/42"],
    "running": ["re-index of the archive"],
    "meta": {"agent": "worker-1", "host": "compute-01", "refs": ["card-7", "#12"]},
}


def _render_violations(data):
    try:
        render_template("notice", data)
    except MessageFormatError as exc:
        return "\n".join(exc.violations)
    return ""


def _violations(subject, body, **context):
    with pytest.raises(MessageFormatError) as info:
        validate_message("notice", subject, body, **context)
    return "\n".join(info.value.violations)


def test_notice_valid_example_passes():
    # Arrange
    subject, body = SUBJECT, BODY
    # Act
    result = validate_message("notice", subject, body, agent="worker-1")
    # Assert
    assert result is None


def test_render_notice_produces_the_documented_layout():
    # Arrange
    data = DATA
    # Act
    rendered = render_template("notice", data)
    # Assert
    assert rendered == (SUBJECT, BODY)


def test_render_notice_accepts_option_text_as_recommendation():
    # Arrange
    data = {**DATA, "questions": [{**DATA["questions"][0], "recommend": "yes"}]}
    # Act
    _, body = render_template("notice", data)
    # Assert
    assert '   reply: "1 A"' in body.splitlines()


def test_render_notice_omits_empty_sections():
    # Arrange
    data = {
        "kind": "DONE",
        "title": "release 1.2.3",
        "done": ["published"],
        "meta": {"agent": "a", "host": "h"},
    }
    # Act
    subject, body = render_template("notice", data)
    # Assert
    assert (subject, body) == (
        "[SciTeX][a] DONE: release 1.2.3",
        f"■ DONE\n  - published\n\n{NOTICE_RULE}\nagent: a | host: h | card/PR: -\n",
    )


def test_render_notice_reports_all_data_problems_at_once():
    # Arrange
    data = {"kind": "LATER", "questions": [{"text": "x", "options": ["only"]}]}
    # Act
    joined = _render_violations(data)
    # Assert
    assert all(
        part in joined
        for part in (
            "kind must be one of",
            "title is empty",
            "meta.agent",
            "two choices",
        )
    )


@pytest.mark.parametrize(
    "subject, expected",
    [
        ("storage quota decision", "subject must be"),
        ("[SciTeX][worker-1] LATER: x", "KIND 'LATER'"),
        ("[SciTeX][worker-1] NEEDS-YOU: two\nlines", "subject must be"),
    ],
)
def test_notice_rejects_bad_subject(subject, expected):
    # Arrange
    body = BODY
    # Act
    joined = _violations(subject, body)
    # Assert
    assert expected in joined


def test_notice_rejects_subject_agent_mismatch():
    # Arrange
    agent = "worker-2"
    # Act
    joined = _violations(SUBJECT, BODY, agent=agent)
    # Assert
    assert "expected 'worker-2'" in joined


def test_notice_rejects_unknown_first_line():
    # Arrange
    body = "Hi Yusuke,\n" + BODY
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "first line must be a section header" in joined


def test_notice_rejects_sections_out_of_order():
    # Arrange
    subject = "[SciTeX][worker-1] DONE: x"
    body = "■ RUNNING (no action needed)\n  - a\n\n■ DONE\n  - b\n" + FOOTER
    # Act
    joined = _violations(subject, body)
    # Assert
    assert "out of order" in joined


def test_notice_needs_you_requires_a_recommended_question():
    # Arrange
    body = "■ DONE\n  - b\n" + FOOTER
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "NEEDS-YOU notice needs" in joined


def test_notice_question_without_recommend_fails():
    # Arrange
    body = BODY.replace("   -> recommend: A\n", "")
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "has no '   -> recommend: X' line" in joined


def test_notice_recommend_must_be_a_listed_option():
    # Arrange
    body = BODY.replace("-> recommend: A", "-> recommend: C").replace('"1 A"', '"1 C"')
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "recommends 'C'" in joined


def test_notice_needs_you_section_requires_needs_you_kind():
    # Arrange
    subject = SUBJECT.replace("NEEDS-YOU", "FYI")
    # Act
    joined = _violations(subject, BODY)
    # Assert
    assert "requires the subject KIND NEEDS-YOU" in joined


def test_notice_requires_footer():
    # Arrange
    body = BODY.split(NOTICE_RULE)[0]
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "footer missing" in joined


def test_notice_footer_agent_must_match_subject():
    # Arrange
    body = BODY.replace("agent: worker-1", "agent: worker-9")
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "footer agent 'worker-9'" in joined


def test_notice_enforces_line_limit():
    # Arrange
    items = "".join(f"  - item {i}\n" for i in range(NOTICE_MAX_LINES))
    body = BODY.replace(
        "■ RUNNING (no action needed)\n", "■ RUNNING (no action needed)\n" + items
    )
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert f"at most {NOTICE_MAX_LINES}" in joined


def test_notice_rejects_prose_items():
    # Arrange
    body = BODY.replace("  - re-index of the archive", "The re-index is going fine.")
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "must be one '  - ' line" in joined


def test_notice_rejects_credential_shaped_text():
    # Arrange
    body = BODY.replace("  - re-index of the archive", "  - password=hunter2hunter2")
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "credential" in joined


def _tiny_render(data):
    return f"[x] {data['t']}", data["t"] + "\n"


def _tiny_validate(subject, body, **_):
    if not subject.startswith("[x] "):
        raise MessageFormatError("tiny", ["subject must start with [x]"])


@pytest.fixture
def tiny_template():
    register_template("tiny-test", _tiny_render, _tiny_validate, replace=True)
    return "tiny-test"


def test_register_template_makes_a_user_template_renderable(tiny_template):
    # Arrange
    data = {"t": "hello"}
    # Act
    rendered = render_template(tiny_template, data)
    # Assert
    assert rendered == ("[x] hello", "hello\n")


def test_register_template_lists_the_user_template(tiny_template):
    # Arrange
    name = tiny_template
    # Act
    names = list_templates()
    # Assert
    assert name in names and "notice" in names


def test_register_template_refuses_a_duplicate_name(tiny_template):
    # Arrange
    call = lambda: register_template(tiny_template, _tiny_render, _tiny_validate)  # noqa: E731
    # Act
    expected = ValueError
    # Assert
    with pytest.raises(expected):
        call()


def test_validate_message_runs_the_user_validator(tiny_template):
    # Arrange
    call = lambda: validate_message(tiny_template, "nope", "body")  # noqa: E731
    # Act
    expected = MessageFormatError
    # Assert
    with pytest.raises(expected):
        call()


def test_unknown_template_is_a_key_error():
    # Arrange
    call = lambda: validate_message("no-such-template", SUBJECT, BODY)  # noqa: E731
    # Act
    expected = KeyError
    # Assert
    with pytest.raises(expected):
        call()


def test_load_message_data_reads_json_and_yaml(tmp_path):
    # Arrange
    yaml = pytest.importorskip("yaml")
    (tmp_path / "n.json").write_text(json.dumps(DATA))
    (tmp_path / "n.yaml").write_text(yaml.safe_dump(DATA))
    # Act
    loaded = [load_message_data(tmp_path / f"n.{ext}") for ext in ("json", "yaml")]
    # Assert
    assert loaded == [DATA, DATA]


# --- readability layout: blank lines, headers, indentation --------------------


def test_notice_line_limit_counts_only_content_lines():
    # Arrange: exactly NOTICE_MAX_LINES content lines plus headers/blank/footer
    head = '■ NEEDS YOU\n1. q?\n   A) a\n   B) b\n   -> recommend: A\n   reply: "1 A"\n'
    bullets = "".join(f"  - item {i}\n" for i in range(NOTICE_MAX_LINES - 5))
    body = head + "\n■ DONE\n" + bullets + FOOTER
    # Act
    result = validate_message("notice", SUBJECT, body)
    # Assert
    assert result is None


@pytest.mark.parametrize(
    "old, new, expected",
    [
        ("\n\n■ DONE", "\n■ DONE", "blank line before section '■ DONE'"),
        ("\n\n" + NOTICE_RULE, "\n" + NOTICE_RULE, "blank line before the footer rule"),
        ("\n\n■ DONE", "\n\n\n■ DONE", "only one blank line at a time"),
        ("   A) yes\n", "   A) yes\n\n", "no blank line inside a question block"),
        ("■ NEEDS YOU\n1.", "■ NEEDS YOU\n\n1.", "no blank line between a header"),
        ("■ DONE", "DONE", "section header 'DONE' must be '■ DONE'"),
        ("  - nightly", "- nightly", "must be one '  - ' line"),
        ("   B) no", "   C) no", "option 'C' should be 'B'"),
        ('"1 A"', '"1 B"', "should accept the recommendation (A)"),
        (
            "   A) yes\n   B) no, prune old runs\n",
            "   A) yes  B) no\n",
            "at least two options",
        ),
        ("  - re-index", "\t- re-index", "contains a tab"),
    ],
)
def test_notice_rejects_layout_violations(old, new, expected):
    # Arrange
    body = BODY.replace(old, new, 1)
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert expected in joined


def test_notice_rejects_the_previous_compact_layout():
    # Arrange: the 0.2.x layout (bare headers, inline options, '--' footer)
    body = (
        'NEEDS YOU\n1. q?\n   A) yes  B) no  -> recommend: A\n   reply: "1 A"\n'
        "--\nagent: worker-1 | host: h | card/PR: -\n"
    )
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert (
        "footer missing" in joined and "first line must be a section header" in joined
    )


def test_notice_accepts_an_ascii_rule():
    # Arrange
    body = BODY.replace(NOTICE_RULE, "-" * 20)
    # Act
    result = validate_message("notice", SUBJECT, body)
    # Assert
    assert result is None


def test_rendered_questions_are_separated_by_one_blank_line():
    # Arrange
    second = {"text": "Second?", "options": ["x", "y"], "recommend": "y"}
    data = {**DATA, "questions": DATA["questions"] + [second]}
    # Act
    _, body = render_template("notice", data)
    # Assert
    assert (
        '   reply: "1 A"\n\n2. Second?\n   A) x\n   B) y\n   -> recommend: B\n' in body
    )


# --- HTML alternative ----------------------------------------------------------


def test_html_alternative_has_headings_lists_and_footer():
    # Arrange
    subject, body = SUBJECT, BODY
    # Act
    page = render_message_html("notice", subject, body)
    # Assert
    assert all(
        part in page
        for part in (
            "<h3",
            ">NEEDS YOU</h3>",
            '<li value="1"',
            "<b>B)</b> no, prune old runs",
            "<code>1 A</code>",
            ">RUNNING (no action needed)</h3>",
            '<a href="https://example.org/run/42">',
            "<hr>",
            "agent: worker-1 | host: compute-01",
        )
    )


def test_html_alternative_escapes_markup():
    # Arrange
    body = BODY.replace("re-index of the archive", "<script>alert(1)</script> & co")
    # Act
    page = render_message_html("notice", SUBJECT, body)
    # Assert
    assert (
        "<script>" not in page
        and "&lt;script&gt;alert(1)&lt;/script&gt; &amp; co" in page
    )


def test_html_alternative_refuses_an_invalid_message():
    # Arrange
    body = "Hi,\n" + BODY
    # Act
    call = lambda: render_message_html("notice", SUBJECT, body)  # noqa: E731
    # Assert
    with pytest.raises(MessageFormatError):
        call()


def test_html_alternative_needs_a_template_html_renderer(tiny_template):
    # Arrange
    call = lambda: render_message_html(tiny_template, "[x] a", "a\n")  # noqa: E731
    # Act
    expected = ValueError
    # Assert
    with pytest.raises(expected):
        call()
