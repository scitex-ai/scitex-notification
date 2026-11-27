#!/usr/bin/env python3
# Timestamp: "2026-01-13 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_backends/_email.py

"""Email notification backend."""

from __future__ import annotations

import asyncio
import os
import re
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, getaddresses
from typing import Optional

from ._types import BaseNotifyBackend, NotifyLevel, NotifyResult


def _getenv_email(*names: str) -> Optional[str]:
    """Return the first non-empty value found among the given env var names."""
    for name in names:
        val = os.getenv(name)
        if val:
            return val
    return None


_MESSAGE_ID = re.compile(r"^<[^<>\s@]+@[^<>\s@]+>$")


def _build_message(
    to: str,
    subject: str,
    body: str,
    from_addr: str,
    message_id: Optional[str] = None,
    from_name: Optional[str] = None,
    html_body: Optional[str] = None,
):
    """Build the plain-text message, optionally with a caller-chosen Message-ID.

    A caller-chosen Message-ID lets the sender later match replies by their
    ``In-Reply-To`` / ``References`` headers. Without one the submission
    server assigns an ID the caller never learns.

    ``from_name`` sets the display name of the ``From`` header
    (``"Name" <addr>``; non-ASCII names are RFC 2047 encoded). It never
    changes the address itself, which stays ``from_addr``.

    ``html_body`` adds an HTML rendering of the same content: the message
    becomes ``multipart/alternative`` with the plain text first, so clients
    that prefer plain text (and every reply quote) still use ``body``.
    """
    if message_id is not None and not _MESSAGE_ID.match(message_id):
        raise ValueError("message_id must look like <local@domain>")
    if from_name is not None and any(c in from_name for c in "\r\n"):
        raise ValueError("from_name must be a single line (no CR/LF)")
    if html_body is not None and not html_body.strip():
        raise ValueError("html_body is empty; omit it for a plain-text message")
    if html_body is None:
        msg = MIMEText(body)
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body))
        msg.attach(MIMEText(html_body, "html"))
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, from_addr)) if from_name else from_addr
    msg["To"] = to
    if message_id is not None:
        msg["Message-ID"] = message_id
    return msg


def _send_email(
    to: str,
    subject: str,
    body: str,
    from_addr: Optional[str] = None,
    password: Optional[str] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    message_id: Optional[str] = None,
    from_name: Optional[str] = None,
    env_fallback: bool = True,
    ssl_context: Optional[ssl.SSLContext] = None,
    html_body: Optional[str] = None,
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
    message_id : str, optional
        Explicit ``Message-ID`` header (``<local@domain>``), so replies can be
        threaded back to this message. Omitted: the server assigns one.
    from_name : str, optional
        Display name for the ``From`` header (``"Name" <from_addr>``). The
        SMTP login and the envelope sender stay the bare address. CR/LF is
        rejected with ``ValueError``.
    html_body : str, optional
        HTML rendering of ``body``; sent as a ``multipart/alternative`` part
        after the plain text. Omitted: a single text/plain message.
    env_fallback : bool
        ``False`` uses exactly the given values and never consults the env
        chains below (a profile must not borrow another identity's password);
        ``from_addr`` and ``smtp_host`` are then required, and no password
        means no SMTP login.
    ssl_context : ssl.SSLContext, optional
        Context for STARTTLS. Default: ``ssl.create_default_context()``, which
        verifies the server certificate and host name against the system CA
        store, so the password is never sent to an unverified server. Pass a
        context with your own CA for a private relay.
    """
    if not env_fallback:
        if not from_addr or not smtp_host:
            raise ValueError("from_addr and smtp_host are required without env fallback")
        msg = _build_message(
            to, subject, body, from_addr, message_id, from_name, html_body
        )
        _deliver(
            msg, to, from_addr, password, smtp_host, smtp_port or 587, ssl_context
        )
        return

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

    msg = _build_message(
        to, subject, body, resolved_from, message_id, from_name, html_body
    )
    _deliver(
        msg,
        to,
        resolved_from,
        resolved_password,
        resolved_host,
        resolved_port,
        ssl_context,
    )


def _envelope_recipients(to: str) -> list[str]:
    """One envelope address per recipient in a ``To`` string.

    ``to`` may list several recipients (``"a@x.org, Name <b@x.org>"``), as the
    ``To`` header does. Passed whole as one RCPT it is a single malformed
    address that a real server rejects, so split it the way the header is read.
    """
    addresses = [addr for _name, addr in getaddresses([to]) if addr]
    if not addresses:
        raise ValueError("no recipient address in 'to'")
    return addresses


def _deliver(msg, to, from_addr, password, host, port, context=None) -> None:
    """Verified STARTTLS submission; login and envelope sender are the bare address.

    The certificate is always verified (a default context when none is given):
    an unverified STARTTLS would hand the SMTP password to any interceptor.
    """
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context or ssl.create_default_context())
        if password:
            server.login(from_addr, password)
        server.send_message(msg, from_addr=from_addr, to_addrs=_envelope_recipients(to))


def send_email(
    to: str,
    subject: str,
    body: str,
    *,
    from_addr: Optional[str] = None,
    password: Optional[str] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    message_id: Optional[str] = None,
    from_name: Optional[str] = None,
    ssl_context: Optional[ssl.SSLContext] = None,
    html_body: Optional[str] = None,
) -> None:
    """Send a plain-text email synchronously with explicit credentials.

    Public, side-channel-free wrapper over :func:`_send_email`. Unlike the
    env-driven :class:`EmailBackend` (which resolves ``from``/``password``
    from *independent* fallback chains and so can pair a sender from one
    identity with a password from another), every field here is passed in
    by the caller — the caller owns the coherent identity. Each argument
    left ``None`` still falls back to the ``SCITEX_NOTIFICATION_EMAIL_*``
    env chain documented on :func:`_send_email`.

    Pass ``message_id`` (``<local@domain>``) to fix the ``Message-ID``
    header, so replies can later be matched via ``In-Reply-To``.
    Pass ``from_name`` to show a display name (``"Name" <from_addr>``) in the
    ``From`` header; the SMTP login and envelope sender stay ``from_addr``.
    STARTTLS verifies the server certificate (``ssl.create_default_context()``
    unless ``ssl_context`` is given). Pass ``html_body`` to add an HTML
    alternative of the same content (``multipart/alternative``, plain first);
    for a template, :func:`~scitex_notification.render_message_html` builds it.

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
        message_id=message_id,
        from_name=from_name,
        ssl_context=ssl_context,
        html_body=html_body,
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
