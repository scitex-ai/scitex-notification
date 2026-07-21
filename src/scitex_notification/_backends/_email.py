#!/usr/bin/env python3
# Timestamp: "2026-01-13 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_backends/_email.py

"""Email notification backend."""

from __future__ import annotations

import asyncio
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional

from ._types import BaseNotifyBackend, NotifyLevel, NotifyResult


def _getenv_email(*names: str) -> Optional[str]:
    """Return the first non-empty value found among the given env var names."""
    for name in names:
        val = os.getenv(name)
        if val:
            return val
    return None


def _send_email(
    to: str,
    subject: str,
    body: str,
    from_addr: Optional[str] = None,
    password: Optional[str] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
) -> None:
    """Send an email via SMTP using stdlib only.

    Parameters
    ----------
    to : str
        Recipient email address.
    subject : str
        Email subject line.
    body : str
        Plain-text email body.
    from_addr : str, optional
        Sender address. Falls back to SCITEX_NOTIFICATION_EMAIL_FROM /
        SCITEX_SCHOLAR_EMAIL_NOREPLY / SCITEX_EMAIL_NOREPLY / SCITEX_EMAIL_AGENT.
    password : str, optional
        SMTP password. Falls back to SCITEX_NOTIFICATION_EMAIL_PASSWORD /
        SCITEX_SCHOLAR_EMAIL_PASSWORD / SCITEX_EMAIL_PASSWORD.
    smtp_host : str, optional
        SMTP host. Falls back to SCITEX_NOTIFICATION_EMAIL_SMTP_HOST
        (default: smtp.gmail.com).
    smtp_port : int, optional
        SMTP port. Falls back to SCITEX_NOTIFICATION_EMAIL_SMTP_PORT
        (default: 587).
    """
    resolved_from = (
        from_addr
        or _getenv_email(
            "SCITEX_NOTIFICATION_EMAIL_FROM",
            "SCITEX_SCHOLAR_EMAIL_NOREPLY",
            "SCITEX_SCHOLAR_FROM_EMAIL_ADDRESS",
            "SCITEX_EMAIL_NOREPLY",
            "SCITEX_EMAIL_AGENT",
        )
        or "no-reply@scitex.ai"
    )

    resolved_password = (
        password
        or _getenv_email(
            "SCITEX_NOTIFICATION_EMAIL_PASSWORD",
            "SCITEX_SCHOLAR_EMAIL_PASSWORD",
            "SCITEX_SCHOLAR_FROM_EMAIL_PASSWORD",
            "SCITEX_EMAIL_PASSWORD",
        )
        or ""
    )

    resolved_host = (
        smtp_host
        or _getenv_email(
            "SCITEX_NOTIFICATION_EMAIL_SMTP_HOST",
        )
        or "smtp.gmail.com"
    )

    resolved_port = smtp_port
    if resolved_port is None:
        port_str = _getenv_email("SCITEX_NOTIFICATION_EMAIL_SMTP_PORT")
        resolved_port = int(port_str) if port_str else 587

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = resolved_from
    msg["To"] = to

    with smtplib.SMTP(resolved_host, resolved_port) as server:
        server.starttls()
        if resolved_password:
            server.login(resolved_from, resolved_password)
        server.send_message(msg)


def send_email(
    to: str,
    subject: str,
    body: str,
    *,
    from_addr: Optional[str] = None,
    password: Optional[str] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
) -> None:
    """Send a plain-text email synchronously with explicit credentials.

    Public, side-channel-free wrapper over :func:`_send_email`. Unlike the
    env-driven :class:`EmailBackend` (which resolves ``from``/``password``
    from *independent* fallback chains and so can pair a sender from one
    identity with a password from another), every field here is passed in
    by the caller — the caller owns the coherent identity. Each argument
    left ``None`` still falls back to the ``SCITEX_NOTIFICATION_EMAIL_*``
    env chain documented on :func:`_send_email`.

    Raises any ``smtplib`` error on failure (fail-loud — no silent ``False``).
    """
    _send_email(
        to=to,
        subject=subject,
        body=body,
        from_addr=from_addr,
        password=password,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
    )


class EmailBackend(BaseNotifyBackend):
    """Email notification via SMTP (stdlib smtplib)."""

    name = "email"

    def __init__(
        self,
        recipient: Optional[str] = None,
        sender: Optional[str] = None,
    ):
        self.recipient = recipient or _getenv_email(
            "SCITEX_NOTIFICATION_EMAIL_TO",
        )
        self.sender = sender or _getenv_email(
            "SCITEX_NOTIFICATION_EMAIL_FROM",
            "SCITEX_SCHOLAR_EMAIL_NOREPLY",
            "SCITEX_SCHOLAR_FROM_EMAIL_ADDRESS",
            "SCITEX_EMAIL_NOREPLY",
            "SCITEX_EMAIL_AGENT",
        )

    def is_available(self) -> bool:
        has_from = bool(
            _getenv_email(
                "SCITEX_NOTIFICATION_EMAIL_FROM",
                "SCITEX_SCHOLAR_EMAIL_NOREPLY",
                "SCITEX_SCHOLAR_FROM_EMAIL_ADDRESS",
                "SCITEX_EMAIL_NOREPLY",
                "SCITEX_EMAIL_AGENT",
            )
        )
        has_password = bool(
            _getenv_email(
                "SCITEX_NOTIFICATION_EMAIL_PASSWORD",
                "SCITEX_SCHOLAR_EMAIL_PASSWORD",
                "SCITEX_SCHOLAR_FROM_EMAIL_PASSWORD",
                "SCITEX_EMAIL_PASSWORD",
            )
        )
        return has_from and has_password

    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        level: NotifyLevel = NotifyLevel.INFO,
        **kwargs,
    ) -> NotifyResult:
        try:
            recipient = kwargs.get("recipient", self.recipient)
            if not recipient:
                raise ValueError(
                    "No recipient configured. Set SCITEX_NOTIFICATION_EMAIL_TO "
                    "or pass recipient= to EmailBackend()."
                )

            subject = title or f"[SciTeX] {level.value.upper()}"

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: _send_email(
                    to=recipient,
                    subject=subject,
                    body=message,
                ),
            )

            return NotifyResult(
                success=True,
                backend=self.name,
                message=message,
                timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            return NotifyResult(
                success=False,
                backend=self.name,
                message=message,
                timestamp=datetime.now().isoformat(),
                error=str(e),
            )


# EOF
