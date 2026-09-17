#!/usr/bin/env python3

"""Telegram notification backend contract tests.

No mocks (repo no-mocks policy — STX-NM002 / audit rule PA-306): the four Bot
API callables are injected through the backend's ``transports`` seam, so the
delivery-receipt contract is exercised by a hand-rolled transport that records
its arguments and returns the response shape the real Bot API returns. The
production default is still the real stdlib-urllib transport; only the tests
substitute.
"""

from __future__ import annotations

import pytest

from scitex_notification._backends._telegram import TelegramBackend
from scitex_notification._backends._types import NotifyLevel


class FakeTelegramTransport:
    """Stand-in for the Bot API callables: records calls, returns a real shape.

    ``message_id`` mirrors ``result.message_id`` from the Bot API; ``error``
    injects a transport failure so the receipt's error path can be observed
    without reaching the network.
    """

    def __init__(self, message_id: int = 456, error: Exception | None = None):
        self.message_id = message_id
        self.error = error
        self.calls: list[tuple] = []

    def __call__(self, token, chat_id, text, caption=""):
        self.calls.append((token, chat_id, text, caption))
        if self.error is not None:
            raise self.error
        return {"ok": True, "result": {"message_id": self.message_id}}


def test_telegram_backend_is_available_with_explicit_credentials():
    # Arrange
    backend = TelegramBackend(bot_token="test-token", chat_id="123")

    # Act
    available = backend.is_available()

    # Assert
    assert available is True


def test_telegram_backend_is_unavailable_without_chat_id():
    # Arrange
    backend = TelegramBackend(bot_token="test-token", chat_id="")

    # Act
    available = backend.is_available()

    # Assert
    assert available is False


@pytest.mark.asyncio
async def test_successful_send_receipts_the_provider_message_id():
    # Arrange
    transport = FakeTelegramTransport(message_id=456)
    backend = TelegramBackend(
        bot_token="test-token", chat_id="123", transports={"message": transport}
    )

    # Act
    result = await backend.send(
        "finished",
        title="Agent",
        level=NotifyLevel.INFO,
        idempotency_key="run-123",
    )

    # Assert
    assert (result.success, result.delivery_id, result.idempotency_key) == (
        True,
        "456",
        "run-123",
    )


@pytest.mark.asyncio
async def test_text_payload_is_the_bold_title_then_the_message():
    # Arrange
    transport = FakeTelegramTransport()
    backend = TelegramBackend(
        bot_token="test-token", chat_id="123", transports={"message": transport}
    )

    # Act
    await backend.send("finished", title="Agent", level=NotifyLevel.INFO)

    # Assert
    assert transport.calls == [("test-token", "123", "*Agent*\nfinished", "")]


@pytest.mark.asyncio
async def test_transport_failure_is_receipted_with_the_token_redacted():
    # Arrange
    token = "secret-bot-token"
    transport = FakeTelegramTransport(
        error=RuntimeError(f"request failed at https://api.telegram.org/bot{token}")
    )
    backend = TelegramBackend(
        bot_token=token, chat_id="123", transports={"message": transport}
    )

    # Act
    result = await backend.send("finished", idempotency_key="run-123")

    # Assert
    assert (
        result.success,
        result.error,
        result.error_code,
        result.idempotency_key,
    ) == (
        False,
        "request failed at https://api.telegram.org/bot<redacted>",
        "delivery_error",
        "run-123",
    )


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])

# EOF
