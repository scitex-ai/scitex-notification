"""Owner consent: URL shape and the real loopback redirect (no mocks)."""

import base64
import hashlib
import socket
import threading
import time
import urllib.parse
import urllib.request

import pytest

from scitex_notification import CalendarError
from scitex_notification._calendar._authorize import (
    build_authorization_url,
    pkce_pair,
    wait_for_code,
)
from scitex_notification._calendar._rules import SCOPES


@pytest.fixture
def consent():
    verifier, challenge = pkce_pair()
    url = build_authorization_url(
        "cid", "http://127.0.0.1:8765/", "dev@example.org", "st", challenge
    )
    return verifier, urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)


def test_consent_url_uses_s256_pkce_of_the_verifier(consent):
    # Arrange
    verifier, query = consent
    digest = hashlib.sha256(verifier.encode()).digest()
    # Act
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    # Assert
    assert (query["code_challenge"], query["code_challenge_method"]) == (
        [expected],
        ["S256"],
    )


def test_consent_url_asks_only_the_narrow_scopes(consent):
    # Arrange
    _, query = consent
    # Act
    scopes = query["scope"]
    # Assert
    assert scopes == [" ".join(SCOPES)]


def test_consent_url_asks_offline_access_for_the_account(consent):
    # Arrange
    _, query = consent
    # Act
    asked = (query["access_type"], query["login_hint"])
    # Assert
    assert asked == (["offline"], ["dev@example.org"])


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _redirect_later(port, query):
    def go():
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/?{query}", timeout=2)
                return
            except OSError:
                time.sleep(0.05)

    thread = threading.Thread(target=go, daemon=True)
    thread.start()
    return thread


def test_loopback_redirect_returns_the_code():
    # Arrange
    port = _free_port()
    thread = _redirect_later(port, "code=abc&state=s1")
    # Act
    code = wait_for_code(port, "s1", timeout_s=10)
    thread.join(5)
    # Assert
    assert code == "abc"


def test_loopback_redirect_with_wrong_state_is_refused():
    # Arrange
    port = _free_port()
    _redirect_later(port, "code=abc&state=forged")
    # Act
    call = lambda: wait_for_code(port, "s1", timeout_s=10)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="state does not match"):
        call()
