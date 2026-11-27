"""Tests for the plain-text email message builder."""

import email
import email.policy
import email.utils
import inspect
import ssl

import pytest

from scitex_notification import send_email
from scitex_notification._backends._email import _build_message


def test_build_message_sets_caller_message_id():
    # Arrange
    message_id = "<abc.123@example.org>"
    # Act
    msg = _build_message(
        "ops@example.org",
        "Subject",
        "Body",
        "agent@example.org",
        message_id=message_id,
    )
    # Assert
    assert email.message_from_string(msg.as_string())["Message-ID"] == message_id


def test_build_message_keeps_addresses_and_subject():
    # Arrange
    expected = ("agent@example.org", "ops@example.org", "Subject")
    # Act
    msg = _build_message(
        "ops@example.org",
        "Subject",
        "Body",
        "agent@example.org",
        message_id="<abc.123@example.org>",
    )
    # Assert
    assert (msg["From"], msg["To"], msg["Subject"]) == expected


def test_build_message_without_message_id_leaves_it_to_server():
    # Arrange
    args = ("ops@example.org", "S", "B", "agent@example.org")
    # Act
    msg = _build_message(*args)
    # Assert
    assert msg["Message-ID"] is None


@pytest.mark.parametrize(
    "bad", ["abc@example.org", "<no-at-sign>", "<a@b>\r\nBcc: x@y", "<a b@c>"]
)
def test_build_message_rejects_malformed_message_id(bad):
    # Arrange
    args = ("ops@example.org", "S", "B", "agent@example.org")
    # Act
    call = lambda: _build_message(*args, message_id=bad)  # noqa: E731
    # Assert
    with pytest.raises(ValueError):
        call()


def test_public_send_email_takes_message_id_as_optional_keyword():
    # Arrange
    params = inspect.signature(send_email).parameters
    # Act
    param = params["message_id"]
    # Assert
    assert (param.kind, param.default) == (inspect.Parameter.KEYWORD_ONLY, None)


def _parsed_from(msg):
    parsed = email.message_from_string(msg.as_string(), policy=email.policy.default)
    return email.utils.getaddresses([str(parsed["From"])])[0]


def test_build_message_from_name_sets_display_name_and_keeps_address():
    # Arrange
    args = ("ops@example.org", "S", "B", "agent@example.org")
    # Act
    msg = _build_message(*args, from_name="SciTeX Agent (worker-1)")
    # Assert
    assert _parsed_from(msg) == ("SciTeX Agent (worker-1)", "agent@example.org")


def test_build_message_from_name_encodes_non_ascii():
    # Arrange
    args = ("ops@example.org", "S", "B", "agent@example.org")
    # Act
    msg = _build_message(*args, from_name="渡邉 エージェント")
    # Assert
    assert msg.as_string().isascii() and _parsed_from(msg) == (
        "渡邉 エージェント",
        "agent@example.org",
    )


def test_build_message_without_from_name_keeps_bare_address():
    # Arrange
    args = ("ops@example.org", "S", "B", "agent@example.org")
    # Act
    msg = _build_message(*args)
    # Assert
    assert msg["From"] == "agent@example.org"


@pytest.mark.parametrize("bad", ["Agent\r\nBcc: x@y", "Agent\nX", "Agent\r"])
def test_build_message_rejects_multiline_from_name(bad):
    # Arrange
    args = ("ops@example.org", "S", "B", "agent@example.org")
    # Act
    call = lambda: _build_message(*args, from_name=bad)  # noqa: E731
    # Assert
    with pytest.raises(ValueError):
        call()


def test_public_send_email_takes_from_name_as_optional_keyword():
    # Arrange
    params = inspect.signature(send_email).parameters
    # Act
    param = params["from_name"]
    # Assert
    assert (param.kind, param.default) == (inspect.Parameter.KEYWORD_ONLY, None)


def test_send_email_from_name_reaches_header_but_not_login_or_envelope(smtp_server):
    # Arrange
    kwargs = dict(
        from_addr="agent@example.org",
        password="local-test-only",
        smtp_host="127.0.0.1",
        smtp_port=smtp_server.port,
        ssl_context=smtp_server.client_context,
        from_name="SciTeX Agent (worker-1)",
    )
    # Act
    send_email("ops@example.org", "Subject", "Body", **kwargs)
    smtp_server.thread.join(timeout=10)
    record = smtp_server.record
    header = email.message_from_bytes(record["data"], policy=email.policy.default)
    # Assert
    assert (
        record["tls"],
        record["login"],
        record["envelope_from"],
        record["envelope_to"],
        email.utils.getaddresses([str(header["From"])])[0],
    ) == (
        True,
        "agent@example.org",
        "<agent@example.org>",
        "<ops@example.org>",
        ("SciTeX Agent (worker-1)", "agent@example.org"),
    )


def test_send_email_refuses_an_unverified_server_certificate(smtp_server):
    # Arrange: the local server's certificate is self-signed, so the default
    # (verifying) context must refuse it before any password is sent.
    kwargs = dict(
        from_addr="agent@example.org",
        password="local-test-only",
        smtp_host="127.0.0.1",
        smtp_port=smtp_server.port,
    )
    call = lambda: send_email("ops@example.org", "S", "B", **kwargs)  # noqa: E731
    # Act
    expected = ssl.SSLCertVerificationError
    # Assert
    with pytest.raises(expected):
        call()


def test_unverified_server_never_receives_the_login(smtp_server):
    # Arrange
    kwargs = dict(
        from_addr="agent@example.org",
        password="local-test-only",
        smtp_host="127.0.0.1",
        smtp_port=smtp_server.port,
    )
    try:
        send_email("ops@example.org", "S", "B", **kwargs)
    except ssl.SSLError:
        pass
    # Act
    smtp_server.thread.join(timeout=10)
    # Assert
    assert "login" not in smtp_server.record
