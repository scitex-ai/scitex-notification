"""Tests for the plain-text email message builder."""

import email
import inspect

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
