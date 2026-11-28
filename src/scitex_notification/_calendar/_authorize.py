#!/usr/bin/env python3
# File: src/scitex_notification/_calendar/_authorize.py

"""One-time owner consent: installed-app OAuth flow with PKCE on loopback."""

from __future__ import annotations

import base64
import hashlib
import http.server
import secrets
import urllib.parse
from typing import Callable, Mapping, Optional

from ._client import TOKEN_URI, GoogleCalendarClient, request_json
from ._credentials import CalendarCredentials, load_credentials, write_private_json
from ._milestone import verify_account
from ._rules import SCOPES, CalendarError

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"


def pkce_pair() -> tuple[str, str]:
    """(verifier, S256 challenge) per RFC 7636."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def build_authorization_url(
    client_id: str, redirect_uri: str, account: str, state: str, code_challenge: str
) -> str:
    """Google consent URL: offline access, the narrow scopes, account hinted."""
    query = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "login_hint": account,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTH_URI}?{urllib.parse.urlencode(query)}"


def wait_for_code(port: int, state: str, timeout_s: float) -> str:
    """Serve one loopback redirect and return its authorization code."""
    captured: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib name
            params = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            captured.update({k: v[0] for k, v in params.items()})
            ok = "code" in captured and captured.get("state") == state
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"scitex-notification: calendar authorized; close this tab."
                if ok
                else b"scitex-notification: authorization failed; see the terminal."
            )

        def log_message(self, *_):  # keep the code out of logs
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    server.timeout = timeout_s
    try:
        server.handle_request()
    finally:
        server.server_close()
    if not captured:
        raise CalendarError(
            f"no browser redirect reached 127.0.0.1:{port} in {timeout_s:.0f} s"
        )
    if captured.get("state") != state:
        raise CalendarError("redirect state does not match; refusing the code")
    if "error" in captured:
        raise CalendarError(f"Google refused authorization: {captured['error']}")
    if "code" not in captured:
        raise CalendarError("redirect carried no authorization code")
    return captured["code"]


def authorize_calendar(
    show_url: Callable[[str], None],
    *,
    port: int = 8765,
    timeout_s: float = 600.0,
    environ: Optional[Mapping[str, str]] = None,
) -> dict:
    """Owner step: consent in a browser, then store the refresh token (0600).

    ``show_url`` receives the consent URL; the owner opens it in a browser
    signed in as the configured account. That browser must reach
    ``127.0.0.1:<port>`` on this host (same machine, or ``ssh -L``). The
    token is saved only after the calendar list proves it is that account's.
    """
    creds = load_credentials(environ, require_token=False)
    redirect_uri = f"http://127.0.0.1:{port}/"
    state = secrets.token_urlsafe(24)
    verifier, challenge = pkce_pair()
    show_url(
        build_authorization_url(
            creds.client_id, redirect_uri, creds.account, state, challenge
        )
    )
    code = wait_for_code(port, state, timeout_s)
    reply = request_json(
        "POST",
        TOKEN_URI,
        form={
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    refresh = reply.get("refresh_token")
    if not refresh:
        raise CalendarError("Google returned no refresh_token (offline consent?)")
    granted = set((reply.get("scope") or "").split())
    missing = [s for s in SCOPES if s not in granted]
    if missing:
        raise CalendarError(f"consent did not grant {missing}; allow every permission")
    probe = GoogleCalendarClient(
        CalendarCredentials(
            account=creds.account,
            client_file=creds.client_file,
            token_file=creds.token_file,
            client_id=creds.client_id,
            client_secret=creds.client_secret,
            refresh_token=refresh,
        ),
        access_token=reply.get("access_token"),
    )
    verify_account(probe.calendar_list(), creds.account)
    write_private_json(
        creds.token_file,
        {"account": creds.account, "refresh_token": refresh, "scopes": list(SCOPES)},
    )
    return {**creds.describe(), "has_token": True, "status": "authorized"}


# EOF
