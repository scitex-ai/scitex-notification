"""Tests for message templates: the built-in ``notice`` and the registry."""

import json

import pytest

from scitex_notification import (
    MessageFormatError,
    list_templates,
    load_message_data,
    register_template,
    render_template,
    validate_message,
)
from scitex_notification._templates import NOTICE_MAX_LINES

SUBJECT = "[SciTeX][worker-1] NEEDS-YOU: storage quota decision"
BODY = """NEEDS YOU
1. Raise the archive quota to 2 TB?
   A) yes  B) no, prune old runs  -> recommend: A
   reply: "1 A"
DONE
- nightly backup verified https://example.org/run/42
RUNNING (no action needed)
- re-index of the archive
--
agent: worker-1 | host: compute-01 | card/PR: card-7, #12
"""

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
        "DONE\n- published\n--\nagent: a | host: h | card/PR: -\n",
    )


def test_render_notice_reports_all_data_problems_at_once():
    # Arrange
    data = {"kind": "LATER", "questions": [{"text": "x", "options": ["only"]}]}
    # Act
    joined = _render_violations(data)
    # Assert
    assert all(
        part in joined
        for part in ("kind must be one of", "title is empty", "meta.agent", "two choices")
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
    body = "RUNNING (no action needed)\n- a\nDONE\n- b\n--\nagent: worker-1 | host: h | card/PR: -\n"
    # Act
    joined = _violations(subject, body)
    # Assert
    assert "out of order" in joined


def test_notice_needs_you_requires_a_recommended_question():
    # Arrange
    body = "DONE\n- b\n--\nagent: worker-1 | host: h | card/PR: -\n"
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "NEEDS-YOU notice needs" in joined


def test_notice_question_without_recommend_fails():
    # Arrange
    body = BODY.replace("  -> recommend: A", "")
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "no options line with '-> recommend: X'" in joined


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
    body = BODY.split("--\n")[0]
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
    items = "".join(f"- item {i}\n" for i in range(NOTICE_MAX_LINES))
    body = BODY.replace(
        "RUNNING (no action needed)\n", "RUNNING (no action needed)\n" + items
    )
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert f"at most {NOTICE_MAX_LINES}" in joined


def test_notice_rejects_prose_items():
    # Arrange
    body = BODY.replace("- re-index of the archive", "The re-index is going fine.")
    # Act
    joined = _violations(SUBJECT, body)
    # Assert
    assert "must be one '- ' line" in joined


def test_notice_rejects_credential_shaped_text():
    # Arrange
    body = BODY.replace("- re-index of the archive", "- password=hunter2hunter2")
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
