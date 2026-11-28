"""Calendar credential files: real files, real modes, no secrets shown."""

import json
import os

import pytest

from scitex_notification import CalendarError, load_credentials


def _client_json(tmp_path, mode=0o600, installed=True):
    path = tmp_path / "client.json"
    section = {"client_id": "id.apps.example", "client_secret": "local-test-only"}
    path.write_text(json.dumps({"installed" if installed else "web": section}))
    os.chmod(path, mode)
    return path


def _token_json(tmp_path, account="dev@example.org"):
    path = tmp_path / "token.json"
    path.write_text(json.dumps({"account": account, "refresh_token": "local-only"}))
    os.chmod(path, 0o600)
    return path


def _env(tmp_path, client, account="dev@example.org"):
    return {
        "SCITEX_NOTIFICATION_GCAL_ACCOUNT": account,
        "SCITEX_NOTIFICATION_GCAL_CLIENT_FILE": str(client),
        "SCITEX_NOTIFICATION_GCAL_TOKEN_FILE": str(tmp_path / "token.json"),
    }


def test_credentials_load_with_a_token(tmp_path):
    # Arrange
    _token_json(tmp_path)
    env = _env(tmp_path, _client_json(tmp_path))
    # Act
    creds = load_credentials(env)
    # Assert
    assert creds.describe()["has_token"] is True


def test_credentials_never_show_secrets(tmp_path):
    # Arrange
    _token_json(tmp_path)
    creds = load_credentials(_env(tmp_path, _client_json(tmp_path)))
    # Act
    shown = repr(creds) + json.dumps(creds.describe())
    # Assert
    assert "local-" not in shown


def test_account_is_required(tmp_path):
    # Arrange
    env = _env(tmp_path, _client_json(tmp_path), account="")
    # Act
    call = lambda: load_credentials(env)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="ACCOUNT is not set"):
        call()


def test_group_readable_client_file_is_refused(tmp_path):
    # Arrange
    env = _env(tmp_path, _client_json(tmp_path, mode=0o644))
    # Act
    call = lambda: load_credentials(env, require_token=False)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="chmod 600"):
        call()


def test_web_oauth_client_is_refused(tmp_path):
    # Arrange
    env = _env(tmp_path, _client_json(tmp_path, installed=False))
    # Act
    call = lambda: load_credentials(env, require_token=False)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="Desktop app"):
        call()


def test_token_for_another_account_is_refused(tmp_path):
    # Arrange
    _token_json(tmp_path, account="someone@example.org")
    env = _env(tmp_path, _client_json(tmp_path))
    # Act
    call = lambda: load_credentials(env)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="authorized for"):
        call()


def test_missing_token_says_where(tmp_path):
    # Arrange
    env = _env(tmp_path, _client_json(tmp_path))
    # Act
    call = lambda: load_credentials(env)  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="does not exist"):
        call()
