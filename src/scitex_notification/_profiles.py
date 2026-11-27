#!/usr/bin/env python3
# File: src/scitex_notification/_profiles.py

"""Named sender/recipient profiles for email, configured only by environment.

A profile bundles one coherent identity — sender, display name, recipient,
SMTP server and credential — under a role name, so a caller says *which
role* sends ("ops", "operator") instead of carrying addresses around. The
package hardcodes no address; every value comes from::

    SCITEX_NOTIFICATION_PROFILE_<NAME>_FROM           sender address (required)
    SCITEX_NOTIFICATION_PROFILE_<NAME>_FROM_NAME      display name (optional)
    SCITEX_NOTIFICATION_PROFILE_<NAME>_TO             recipient address (required)
    SCITEX_NOTIFICATION_PROFILE_<NAME>_SMTP_HOST      SMTP host (required)
    SCITEX_NOTIFICATION_PROFILE_<NAME>_SMTP_PORT      SMTP port (default 587)
    SCITEX_NOTIFICATION_PROFILE_<NAME>_PASSWORD       SMTP password, or
    SCITEX_NOTIFICATION_PROFILE_<NAME>_PASSWORD_FILE  file holding it (mode 0600), or
    SCITEX_NOTIFICATION_PROFILE_<NAME>_PASSWORD_GPG   gpg ciphertext of it, decrypted
                                                      in memory (non-interactive)
    SCITEX_NOTIFICATION_PROFILE_<NAME>_GNUPGHOME      gpg --homedir for that (optional)

``<NAME>`` is the profile name upper-cased with ``-`` turned into ``_``.
"""

from __future__ import annotations

import os
import re
import ssl
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Union

from ._backends._email import _send_email
from ._rate_limit import RateLimiter
from ._templates import validate_message

__all__ = ["Profile", "ProfileError", "get_profile", "send_with_profile"]

_PREFIX = "SCITEX_NOTIFICATION_PROFILE_"
_ADDRESS = re.compile(r"^[^@\s,<>\"']+@[^@\s,<>\"']+\.[^@\s,<>\"']+$")


class ProfileError(ValueError):
    """A profile is missing or misconfigured."""


@dataclass(frozen=True)
class Profile:
    """One sending identity. ``password`` is never shown in ``repr``."""

    name: str
    from_addr: str
    to: str
    smtp_host: str
    smtp_port: int = 587
    from_name: Optional[str] = None
    password: Optional[str] = field(default=None, repr=False)

    def describe(self) -> dict:
        """A JSON-safe summary without the credential."""
        return {
            "profile": self.name,
            "from": self.from_addr,
            "from_name": self.from_name,
            "to": self.to,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "has_password": bool(self.password),
        }


def _env_key(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name or ""):
        raise ProfileError("profile name must be 1-64 characters of [A-Za-z0-9_-]")
    return _PREFIX + name.upper().replace("-", "_") + "_"


def _read_password_file(path: str, variable: str) -> str:
    file = Path(path).expanduser()
    try:
        info = file.stat()
    except OSError as exc:
        raise ProfileError(f"{variable}: cannot read {file} ({type(exc).__name__})")
    if not stat.S_ISREG(info.st_mode):
        raise ProfileError(f"{variable}: {file} is not a regular file")
    if info.st_mode & 0o077:
        raise ProfileError(
            f"{variable}: {file} must not be readable by group/others "
            f"(mode {stat.S_IMODE(info.st_mode):04o}; chmod 600 it)"
        )
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ProfileError(f"{variable}: {file} is not owned by the current user")
    return file.read_text(encoding="utf-8").rstrip("\r\n")


def _decrypt_password_gpg(path: str, homedir: Optional[str], variable: str) -> str:
    """``gpg --batch --decrypt`` into memory: never prompts, never writes.

    A key that needs a passphrase, or no key at all, is a :class:`ProfileError`
    naming the variable and gpg's exit code, not a silent empty password.
    gpg's stderr tail is kept for diagnosis; it never carries the plaintext.
    """
    cmd = ["gpg"]
    if homedir:
        cmd += ["--homedir", str(Path(homedir).expanduser())]
    cmd += ["--quiet", "--batch", "--no-tty", "--decrypt", str(Path(path).expanduser())]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    except FileNotFoundError:
        raise ProfileError(f"{variable}: gpg is not installed")
    except subprocess.TimeoutExpired:
        raise ProfileError(f"{variable}: gpg timed out (passphrase prompt?)")
    password = proc.stdout.decode("utf-8", "replace").rstrip("\r\n")
    if proc.returncode != 0 or not password:
        tail = proc.stderr.decode("utf-8", "replace").strip()[-300:]
        raise ProfileError(
            f"{variable}: cannot decrypt {path} non-interactively "
            f"(gpg rc={proc.returncode})" + (f": {tail}" if tail else "")
        )
    return password


def get_profile(name: str, environ: Optional[Mapping[str, str]] = None) -> Profile:
    """Resolve profile ``name`` from ``SCITEX_NOTIFICATION_PROFILE_<NAME>_*``.

    Raises :class:`ProfileError` naming every missing or invalid variable.
    ``environ`` defaults to ``os.environ``.
    """
    env = os.environ if environ is None else environ
    prefix = _env_key(name)

    def get(suffix: str) -> Optional[str]:
        value = env.get(prefix + suffix)
        return value if value not in (None, "") else None

    problems = []
    values = {s: get(s) for s in ("FROM", "TO", "SMTP_HOST")}
    for suffix, value in values.items():
        if value is None:
            problems.append(f"{prefix}{suffix} is not set")
        elif suffix != "SMTP_HOST" and not _ADDRESS.match(value):
            problems.append(f"{prefix}{suffix} is not a single email address")
    from_name = get("FROM_NAME")
    if from_name and ("\r" in from_name or "\n" in from_name):
        problems.append(f"{prefix}FROM_NAME must be a single line")
    port_text = get("SMTP_PORT") or "587"
    try:
        port = int(port_text)
        if not 0 < port < 65536:
            raise ValueError
    except ValueError:
        problems.append(f"{prefix}SMTP_PORT must be a TCP port number")
        port = 0
    password, password_file = get("PASSWORD"), get("PASSWORD_FILE")
    password_gpg = get("PASSWORD_GPG")
    sources = [
        s
        for s, v in (
            ("PASSWORD", password),
            ("PASSWORD_FILE", password_file),
            ("PASSWORD_GPG", password_gpg),
        )
        if v
    ]
    if len(sources) > 1:
        problems.append("set only one of " + " and ".join(prefix + s for s in sources))
    elif password_file:
        try:
            password = _read_password_file(password_file, prefix + "PASSWORD_FILE")
        except ProfileError as exc:
            problems.append(str(exc))
    elif password_gpg and not problems:
        # Decrypt last, and only for an otherwise usable profile, so a
        # misconfigured profile never spends a gpg call.
        try:
            password = _decrypt_password_gpg(
                password_gpg, get("GNUPGHOME"), prefix + "PASSWORD_GPG"
            )
        except ProfileError as exc:
            problems.append(str(exc))
    if problems:
        raise ProfileError(
            f"profile {name!r} is not usable:\n  - " + "\n  - ".join(problems)
        )
    return Profile(
        name=name,
        from_addr=values["FROM"],
        to=values["TO"],
        smtp_host=values["SMTP_HOST"],
        smtp_port=port,
        from_name=from_name,
        password=password,
    )


def send_with_profile(
    profile: Union[str, Profile],
    subject: str,
    body: str,
    *,
    message_id: Optional[str] = None,
    dedupe_key: Optional[str] = None,
    dedupe_window_s: Optional[float] = None,
    dry_run: bool = False,
    template: Optional[str] = None,
    template_context: Optional[Mapping[str, Any]] = None,
    rate_limit_dir: Optional[Union[str, Path]] = None,
    ssl_context: Optional[ssl.SSLContext] = None,
    html_body: Optional[str] = None,
) -> dict:
    """Send ``subject``/``body`` as ``profile`` (a name or a :class:`Profile`).

    Order of checks, all before any network traffic:

    1. ``template`` given -> :func:`validate_message` (raises
       :class:`~scitex_notification.MessageFormatError`), also on ``dry_run``.
    2. ``dedupe_key`` given -> at most one send per key per
       ``dedupe_window_s`` (required with a key); a repeat returns
       ``status="suppressed"`` without sending. A failed send is not recorded,
       so its retry is not suppressed. ``dry_run`` only peeks.

    Returns a dict with ``status`` (``sent`` / ``dry_run`` / ``suppressed``),
    the From/To used and the message id. SMTP errors propagate (fail loud).
    STARTTLS verifies the server certificate; ``ssl_context`` overrides the
    default context (for a private CA). ``html_body`` adds an HTML
    alternative of the same content (see
    :func:`~scitex_notification.render_message_html`).
    """
    resolved = get_profile(profile) if isinstance(profile, str) else profile
    if not subject or "\r" in subject or "\n" in subject:
        raise ValueError("subject must be a non-empty single line")
    if not body or not body.strip():
        raise ValueError("body is empty")
    if template:
        validate_message(template, subject, body, **dict(template_context or {}))
    if (dedupe_key is None) != (dedupe_window_s is None):
        raise ValueError("dedupe_key and dedupe_window_s go together")
    result = {
        **{k: v for k, v in resolved.describe().items() if k != "has_password"},
        "subject": subject,
        "message_id": message_id,
        "template": template,
        "dedupe_key": dedupe_key,
        "html": html_body is not None,
    }
    limiter = (
        RateLimiter(dedupe_window_s, rate_limit_dir) if dedupe_key is not None else None
    )

    def deliver() -> None:
        _send_email(
            resolved.to,
            subject,
            body,
            env_fallback=False,
            from_addr=resolved.from_addr,
            from_name=resolved.from_name,
            password=resolved.password,
            smtp_host=resolved.smtp_host,
            smtp_port=resolved.smtp_port,
            message_id=message_id,
            ssl_context=ssl_context,
            html_body=html_body,
        )

    if dry_run:
        allowed = limiter.peek(dedupe_key) if limiter else True
        return {**result, "status": "dry_run", "would_send": allowed}
    if limiter is None:
        deliver()
        return {**result, "status": "sent"}
    with limiter.hold(dedupe_key) as allowed:
        if allowed:
            deliver()
    return {**result, "status": "sent" if allowed else "suppressed"}


# EOF
