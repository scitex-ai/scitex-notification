#!/usr/bin/env python3

"""Telegram notification backend contract tests."""

from __future__ import annotations

import pytest

from scitex_notification._backends._telegram import TelegramBackend
from scitex_notification._backends._types import NotifyLevel


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
async def test_telegram_backend_sends_through_bot_api(monkeypatch):
    # Arrange
    sent: list[tuple[str, str, str]] = []
    backend = TelegramBackend(bot_token="test-token", chat_id="123")
    monkeypatch.setattr(
        "scitex_notification._backends._telegram._send_message",
        lambda token, chat_id, text: (
            sent.append((token, chat_id, text))
            or {"ok": True, "result": {"message_id": 456}}
        ),
    )

    # Act
    result = await backend.send(
        "finished",
        title="Agent",
        level=NotifyLevel.INFO,
        idempotency_key="run-123",
    )

    # Assert
    assert (result.success, result.delivery_id, result.idempotency_key, sent) == (
        True,
        "456",
        "run-123",
        [("test-token", "123", "*Agent*\nfinished")],
    )


@pytest.mark.asyncio
async def test_telegram_backend_redacts_token_from_transport_error(monkeypatch):
    # Arrange
    token = "secret-bot-token"
    backend = TelegramBackend(bot_token=token, chat_id="123")

    def _fail(*_args):
        raise RuntimeError(f"request failed at https://api.telegram.org/bot{token}")

    monkeypatch.setattr(
        "scitex_notification._backends._telegram._send_message",
        _fail,
    )

    # Act
    result = await backend.send("finished")

    # Assert
    assert result.error == "request failed at https://api.telegram.org/bot<redacted>"
