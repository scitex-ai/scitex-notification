#!/usr/bin/env python3
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_backends/_telegram.py

"""Telegram notification backend.

Sends messages, images, and voice notes via Telegram Bot API.
No SDK dependency — uses stdlib urllib only (same pattern as Twilio backend).

Environment Variables:
    SCITEX_NOTIFICATION_TELEGRAM_TOKEN: Telegram Bot token (from @BotFather)
    SCITEX_NOTIFICATION_TELEGRAM_CHAT_ID: Target chat ID
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from ._types import BaseNotifyBackend, NotifyLevel, NotifyResult

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


def _getenv_telegram(*names: str) -> str:
    """Return the first non-empty value among the given env var names."""
    for name in names:
        val = os.getenv(name)
        if val:
            return val
    return ""


def _redact_token(value: str, token: str) -> str:
    """Remove a bot credential from an error before it crosses the API boundary."""
    return value.replace(token, "<redacted>") if token else value


class TelegramBackend(BaseNotifyBackend):
    """Telegram message notification backend."""

    name = "telegram"

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        self.bot_token = bot_token or _getenv_telegram(
            "SCITEX_NOTIFICATION_TELEGRAM_TOKEN",
        )
        self.chat_id = chat_id or _getenv_telegram(
            "SCITEX_NOTIFICATION_TELEGRAM_CHAT_ID",
        )

    def is_available(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        level: NotifyLevel = NotifyLevel.INFO,
        **kwargs,
    ) -> NotifyResult:
        idempotency_key = kwargs.get("idempotency_key")
        try:
            chat_id = kwargs.get("chat_id") or self.chat_id
            image_path = kwargs.get("image_path")
            voice_path = kwargs.get("voice_path")
            document_path = kwargs.get("document_path")

            if not all([self.bot_token, chat_id]):
                raise ValueError(
                    "Telegram requires: bot_token, chat_id. "
                    "Set SCITEX_NOTIFICATION_TELEGRAM_TOKEN/CHAT_ID env vars."
                )

            full_message = _format_message(message, title, level)
            loop = asyncio.get_event_loop()

            # Send image if provided
            if image_path and Path(image_path).exists():
                response = await loop.run_in_executor(
                    None,
                    lambda: _send_photo(
                        self.bot_token, chat_id, image_path, full_message
                    ),
                )
            # Send voice note if provided
            elif voice_path and Path(voice_path).exists():
                response = await loop.run_in_executor(
                    None,
                    lambda: _send_voice(
                        self.bot_token, chat_id, voice_path, full_message
                    ),
                )
            # Send document if provided
            elif document_path and Path(document_path).exists():
                response = await loop.run_in_executor(
                    None,
                    lambda: _send_document(
                        self.bot_token, chat_id, document_path, full_message
                    ),
                )
            else:
                # Text-only message
                response = await loop.run_in_executor(
                    None,
                    lambda: _send_message(self.bot_token, chat_id, full_message),
                )

            provider_result = response.get("result", {}) if response else {}
            delivery_id = provider_result.get("message_id")
            return NotifyResult(
                success=True,
                backend=self.name,
                message=message,
                timestamp=datetime.now().isoformat(),
                details={
                    "chat_id": str(chat_id),
                    "idempotency_enforced": False,
                },
                delivery_id=str(delivery_id) if delivery_id is not None else None,
                idempotency_key=idempotency_key,
            )
        except Exception as e:
            error_code = (
                "configuration_error"
                if isinstance(e, ValueError)
                else "delivery_error"
            )
            return NotifyResult(
                success=False,
                backend=self.name,
                message=message,
                timestamp=datetime.now().isoformat(),
                error=_redact_token(str(e), self.bot_token),
                idempotency_key=idempotency_key,
                error_code=error_code,
            )


def _format_message(
    message: str,
    title: Optional[str],
    level: NotifyLevel,
) -> str:
    """Format message with title and level prefix."""
    prefix = ""
    if level == NotifyLevel.CRITICAL:
        prefix = "🔴 CRITICAL: "
    elif level == NotifyLevel.ERROR:
        prefix = "🟠 ERROR: "
    elif level == NotifyLevel.WARNING:
        prefix = "🟡 WARNING: "

    if title:
        return f"{prefix}*{title}*\n{message}"
    return f"{prefix}{message}"


def _telegram_request(token: str, method: str, data: dict) -> dict:
    """Make a Telegram Bot API request (JSON body, no SDK)."""
    url = f"{TELEGRAM_API_BASE.format(token=token)}/{method}"
    body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read().decode())

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result.get('description', 'unknown')}"
        )
    return result


def _telegram_multipart_request(
    token: str,
    method: str,
    fields: dict,
    file_field: str,
    file_path: str,
) -> dict:
    """Make a Telegram Bot API multipart/form-data request for file uploads."""
    boundary = "----ScitexBoundary"
    body = b""

    # Add form fields
    for key, value in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()

    # Add file
    filename = Path(file_path).name
    body += f"--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"\r\n'
    ).encode()
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += Path(file_path).read_bytes()
    body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    url = f"{TELEGRAM_API_BASE.format(token=token)}/{method}"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read().decode())

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result.get('description', 'unknown')}"
        )
    return result


def _send_message(token: str, chat_id: str, text: str) -> dict:
    """Send a text message via Telegram Bot API."""
    # Telegram has a 4096 char limit; truncate if needed
    if len(text) > 4096:
        text = text[:4090] + "\n..."

    return _telegram_request(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        },
    )


def _send_photo(
    token: str, chat_id: str, photo_path: str, caption: str = ""
) -> dict:
    """Send a photo via Telegram Bot API."""
    fields = {"chat_id": chat_id}
    if caption:
        fields["caption"] = caption[:1024]  # Telegram caption limit
        fields["parse_mode"] = "Markdown"

    return _telegram_multipart_request(
        token, "sendPhoto", fields, "photo", photo_path
    )


def _send_voice(
    token: str, chat_id: str, voice_path: str, caption: str = ""
) -> dict:
    """Send a voice note via Telegram Bot API."""
    fields = {"chat_id": chat_id}
    if caption:
        fields["caption"] = caption[:1024]
        fields["parse_mode"] = "Markdown"

    return _telegram_multipart_request(
        token, "sendVoice", fields, "voice", voice_path
    )


def _send_document(
    token: str, chat_id: str, doc_path: str, caption: str = ""
) -> dict:
    """Send a document via Telegram Bot API."""
    fields = {"chat_id": chat_id}
    if caption:
        fields["caption"] = caption[:1024]
        fields["parse_mode"] = "Markdown"

    return _telegram_multipart_request(
        token, "sendDocument", fields, "document", doc_path
    )


# EOF
