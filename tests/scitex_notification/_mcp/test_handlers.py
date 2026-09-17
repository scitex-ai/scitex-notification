#!/usr/bin/env python3

"""Tests for the MCP notify handler's argument routing.

The `notify` tool schema declares send-level arguments (``idempotency_key``)
next to constructor-level ones. ``notify_handler`` receives them all as one flat
mapping and forwarded that whole mapping into BOTH the backend constructor and
``send()``. Every backend constructor is strict — ``WebhookBackend(url=None)``,
``TelegramBackend(bot_token, chat_id)`` — so any send-level argument raised
``TypeError`` inside construction and ``send()`` was never called: the
notification silently never happened and the caller got a generic failure with
no delivery receipt.

No mocks (repo no-mocks policy — STX-NM002 / audit rule PA-306): every case here
drives the real handler, the real backend registry and the real backend classes.
The fake Bot API transport is a hand-rolled callable injected through the
backend's documented ``transports`` seam, and the absent Telegram credentials the
config-error case needs come from a yield fixture that unsets the two env vars
and restores them, not from monkeypatch.
"""

from __future__ import annotations

import os

import pytest

from scitex_notification._backends import WebhookBackend
from scitex_notification._backends._telegram import TelegramBackend
from scitex_notification._mcp.handlers import _constructor_kwargs, notify_handler

_TELEGRAM_ENV_VARS = (
    "SCITEX_NOTIFICATION_TELEGRAM_TOKEN",
    "SCITEX_NOTIFICATION_TELEGRAM_CHAT_ID",
)


@pytest.fixture
def telegram_credentials_absent():
    """Run with Telegram credentials unset, restoring the exact env after."""
    saved = {name: os.environ.pop(name, None) for name in _TELEGRAM_ENV_VARS}
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is not None:
                os.environ[name] = value


class RecordingTransport:
    """Hand-rolled fake Bot API transport: records what it was asked to send."""

    def __init__(self):
        self.calls: list[tuple] = []

    def __call__(self, token, chat_id, text, caption=""):
        self.calls.append((token, chat_id, text))
        return {"ok": True, "result": {"message_id": 456}}


class TestConstructorKwargs:
    def test_keeps_only_the_keywords_the_constructor_accepts(self):
        # Arrange
        kwargs = {"url": "https://example.invalid/hook", "idempotency_key": "run-1"}

        # Act
        accepted = _constructor_kwargs(WebhookBackend, kwargs)

        # Assert
        assert accepted == {"url": "https://example.invalid/hook"}

    def test_drops_send_level_file_arguments(self):
        # Arrange
        kwargs = {"bot_token": "t", "chat_id": "1", "image_path": "x.png"}

        # Act
        accepted = _constructor_kwargs(TelegramBackend, kwargs)

        # Assert
        assert accepted == {"bot_token": "t", "chat_id": "1"}

    def test_passes_everything_to_a_constructor_that_takes_kwargs(self):
        # Arrange
        class Liberal:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        kwargs = {"idempotency_key": "run-1", "image_path": "x.png"}

        # Act
        accepted = _constructor_kwargs(Liberal, kwargs)

        # Assert
        assert accepted == kwargs


class TestNotifyHandlerArgumentRouting:
    @pytest.mark.asyncio
    async def test_idempotency_key_no_longer_breaks_backend_construction(self):
        # Arrange
        # Regression: this returned "WebhookBackend.__init__() got an unexpected
        # keyword argument 'idempotency_key'" and send() was never reached. An
        # empty url is a real config-error input, so the case needs no network.
        # Act
        out = await notify_handler(
            message="boundary probe", backend="webhook", url="", idempotency_key="run-1"
        )

        # Assert
        assert (out["results"][0]["success"], out["results"][0]["error"]) == (
            False,
            "No webhook URL configured",
        )

    @pytest.mark.asyncio
    async def test_idempotency_key_reaches_send_and_returns_in_the_receipt(
        self, telegram_credentials_absent
    ):
        # Arrange
        # Act
        out = await notify_handler(
            message="boundary probe", backend="telegram", idempotency_key="run-1"
        )

        # Assert
        assert (
            out["results"][0]["success"],
            out["results"][0]["error_code"],
            out["results"][0]["idempotency_key"],
        ) == (False, "configuration_error", "run-1")

    @pytest.mark.asyncio
    async def test_injected_transport_receipts_the_provider_message_id(self):
        # Arrange
        transport = RecordingTransport()

        # Act
        out = await notify_handler(
            message="boundary probe",
            backend="telegram",
            bot_token="test-token",
            chat_id="123",
            transports={"message": transport},
            idempotency_key="run-1",
        )

        # Assert
        entry = out["results"][0]
        assert (
            entry["success"],
            entry["delivery_id"],
            entry["idempotency_key"],
            transport.calls,
        ) == (True, "456", "run-1", [("test-token", "123", "boundary probe")])

    @pytest.mark.asyncio
    async def test_missing_idempotency_key_leaves_the_receipt_field_empty(self):
        # Arrange
        # Act
        out = await notify_handler(message="boundary probe", backend="webhook", url="")

        # Assert
        assert (
            out["results"][0]["success"],
            out["results"][0]["idempotency_key"],
        ) == (False, None)


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])

# EOF
