#!/usr/bin/env python3
# File: src/scitex_notification/_calendar/_credentials.py

"""Where the calendar credential lives, configured only by environment.

::

    SCITEX_NOTIFICATION_GCAL_ACCOUNT      account the entries must be written as
                                          (required)
    SCITEX_NOTIFICATION_GCAL_CLIENT_FILE  Google "Desktop app" OAuth client JSON
                                          (mode 0600; default
                                          $SCITEX_DIR/notification/secrets/gcal-client.json)
    SCITEX_NOTIFICATION_GCAL_TOKEN_FILE   refresh token written by
                                          ``scitex-notification calendar authorize``
                                          (mode 0600; default
                                          $SCITEX_DIR/notification/secrets/gcal-token.json)

No secret is ever printed or put into a result.
"""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from ._rules import CalendarError

ENV_PREFIX = "SCITEX_NOTIFICATION_GCAL_"
_ADDRESS = re.compile(r"^[^@\s,<>\"']+@[^@\s,<>\"']+\.[^@\s,<>\"']+$")


def secrets_dir(environ: Mapping[str, str]) -> Path:
    root = Path(environ.get("SCITEX_DIR") or str(Path.home() / ".scitex"))
    return root.expanduser() / "notification" / "secrets"


def private_file(path: Path, variable: str) -> Path:
    """``path`` if it is a regular 0600-style file owned by this user."""
    try:
        info = path.stat()
    except FileNotFoundError:
        raise CalendarError(f"{variable}: {path} does not exist")
    except OSError as exc:
        raise CalendarError(f"{variable}: cannot read {path} ({type(exc).__name__})")
    if not stat.S_ISREG(info.st_mode):
        raise CalendarError(f"{variable}: {path} is not a regular file")
    if info.st_mode & 0o077:
        raise CalendarError(
            f"{variable}: {path} must not be readable by group/others "
            f"(mode {stat.S_IMODE(info.st_mode):04o}; chmod 600 it)"
        )
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise CalendarError(f"{variable}: {path} is not owned by the current user")
    return path


def write_private_json(path: Path, data: Mapping[str, Any]) -> None:
    """Atomically write ``data`` to ``path`` with mode 0600."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(dict(data), stream)
    os.replace(temp, path)


@dataclass(frozen=True)
class CalendarCredentials:
    """The account plus OAuth client and token; secrets stay out of ``repr``."""

    account: str
    client_file: Path
    token_file: Path
    client_id: str = ""
    client_secret: str = field(default="", repr=False)
    refresh_token: str = field(default="", repr=False)

    def describe(self) -> dict:
        """A JSON-safe summary without any secret."""
        return {
            "account": self.account,
            "client_file": str(self.client_file),
            "token_file": str(self.token_file),
            "has_client": bool(self.client_id and self.client_secret),
            "has_token": bool(self.refresh_token),
        }


def _paths(environ: Mapping[str, str]) -> tuple[str, Path, Path]:
    account = (environ.get(ENV_PREFIX + "ACCOUNT") or "").strip()
    if not account:
        raise CalendarError(f"{ENV_PREFIX}ACCOUNT is not set (the account to write as)")
    if not _ADDRESS.match(account):
        raise CalendarError(f"{ENV_PREFIX}ACCOUNT is not a single email address")
    base = secrets_dir(environ)
    client = Path(environ.get(ENV_PREFIX + "CLIENT_FILE") or base / "gcal-client.json")
    token = Path(environ.get(ENV_PREFIX + "TOKEN_FILE") or base / "gcal-token.json")
    return account, client.expanduser(), token.expanduser()


def _read_json(path: Path, variable: str) -> dict:
    try:
        data = json.loads(private_file(path, variable).read_text("utf-8"))
    except ValueError:
        raise CalendarError(f"{variable}: {path} is not JSON")
    if not isinstance(data, dict):
        raise CalendarError(f"{variable}: {path} is not a JSON object")
    return data


def _read_client(path: Path) -> tuple[str, str]:
    variable = ENV_PREFIX + "CLIENT_FILE"
    installed = _read_json(path, variable).get("installed")
    if not isinstance(installed, dict):
        raise CalendarError(
            f"{variable}: {path} is not a Google 'Desktop app' OAuth client "
            "(no 'installed' section)"
        )
    client_id = installed.get("client_id")
    client_secret = installed.get("client_secret")
    if not client_id or not client_secret:
        raise CalendarError(f"{variable}: {path} lacks client_id/client_secret")
    return client_id, client_secret


def load_credentials(
    environ: Optional[Mapping[str, str]] = None, *, require_token: bool = True
) -> CalendarCredentials:
    """Resolve the credential from ``SCITEX_NOTIFICATION_GCAL_*``.

    ``require_token=False`` is for ``authorize``, which creates the token.
    """
    env = os.environ if environ is None else environ
    account, client_file, token_file = _paths(env)
    client_id, client_secret = _read_client(client_file)
    refresh_token = ""
    if require_token:
        variable = ENV_PREFIX + "TOKEN_FILE"
        data = _read_json(token_file, variable)
        refresh_token = data.get("refresh_token") or ""
        if not refresh_token:
            raise CalendarError(f"{variable}: {token_file} has no refresh_token")
        if (data.get("account") or "").lower() != account.lower():
            raise CalendarError(
                f"{variable} was authorized for {data.get('account')!r}, "
                f"not {account!r}; run `scitex-notification calendar authorize`"
            )
    return CalendarCredentials(
        account=account,
        client_file=client_file,
        token_file=token_file,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
    )


# EOF
