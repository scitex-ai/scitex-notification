#!/usr/bin/env python3
"""Tests for the MCP notify handler's argument routing.

The `notify` tool schema declares send-level arguments (``idempotency_key``)
next to constructor-level ones. ``notify_handler`` receives them all as one flat
mapping and forwarded that whole mapping into BOTH the backend constructor and
``send()``. Every backend constructor is strict — ``WebhookBackend(url=None)``,
``TelegramBackend(bot_token, chat_id)`` — so any send-level argument made
construction raise ``TypeError`` before ``send()`` was ever called: the
notification silently never happened and the caller got a generic failure with
no delivery receipt.
"""

from __future__ import annotations

import pytest

from scitex_notification._backends import BACKENDS, WebhookBackend
from scitex_notification._backends._telegram import TelegramBackend
from scitex_notification._backends._types import (
    BaseNotifyBackend,
    NotifyLevel,
    NotifyResult,
)
from scitex_notification._mcp.handlers import _constructor_kwargs, notify_handler


class _RecordingBackend(BaseNotifyBackend):
    """Backend with a strict constructor that records what reached it."""

    name = "recording"
    constructed_with: dict = {}
    sent_with: dict = {}

    def __init__(self, recipient=None):
        type(self).constructed_with = {"recipient": recipient}

    def is_available(self) -> bool:
        return True

    async def send(
        self,
        message: str,
        title=None,
        level: NotifyLevel = NotifyLevel.INFO,
        **kwargs,
    ) -> NotifyResult:
        type(self).sent_with = dict(kwargs)
        return NotifyResult(
            success=True,
            backend=self.name,
            message=message,
            timestamp="2026-09-16T00:00:00",
            idempotency_key=kwargs.get("idempotency_key"),
        )


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
    async def test_idempotency_key_reaches_send_and_not_the_constructor(
        self, monkeypatch
    ):
        # Arrange
        monkeypatch.setitem(BACKENDS, "recording", _RecordingBackend)

        # Act
        out = await notify_handler(
            message="boundary probe",
            backend="recording",
            recipient="ops",
            idempotency_key="run-1",
        )

        # Assert
        assert (
            _RecordingBackend.constructed_with,
            _RecordingBackend.sent_with.get("idempotency_key"),
            out["success_count"],
        ) == ({"recipient": "ops"}, "run-1", 1)

    @pytest.mark.asyncio
    async def test_webhook_construction_accepts_idempotency_key(self, monkeypatch):
        # Arrange
        # Regression: this raised TypeError — "unexpected keyword argument
        # 'idempotency_key'" — so send() was never reached.
        def _injected_transport_failure(*_args, **_kwargs):
            raise RuntimeError("injected transport failure")

        monkeypatch.setattr(
            "scitex_notification._backends._webhook.urllib.request.urlopen",
            _injected_transport_failure,
        )

        # Act
        out = await notify_handler(
            message="boundary probe",
            backend="webhook",
            url="https://example.invalid/hook",
            idempotency_key="run-1",
        )

        # Assert
        entry = out["results"][0]
        assert (entry["success"], entry["error"]) == (
            False,
            "injected transport failure",
        )

    @pytest.mark.asyncio
    async def test_telegram_receipt_fields_surface_in_the_mcp_result(self, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            "scitex_notification._backends._telegram._send_message",
            lambda token, chat_id, text: {"ok": True, "result": {"message_id": 456}},
        )

        # Act
        out = await notify_handler(
            message="boundary probe",
            backend="telegram",
            bot_token="test-token",
            chat_id="123",
            idempotency_key="run-1",
        )

        # Assert
        entry = out["results"][0]
        assert (
            entry["success"],
            entry["delivery_id"],
            entry["idempotency_key"],
            entry["error_code"],
        ) == (True, "456", "run-1", None)

    @pytest.mark.asyncio
    async def test_missing_idempotency_key_leaves_receipt_field_empty(self, monkeypatch):
        # Arrange
        monkeypatch.setitem(BACKENDS, "recording", _RecordingBackend)

        # Act
        out = await notify_handler(message="boundary probe", backend="recording")

        # Assert
        entry = out["results"][0]
        assert (entry["success"], entry["idempotency_key"]) == (True, None)


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])

# EOF
