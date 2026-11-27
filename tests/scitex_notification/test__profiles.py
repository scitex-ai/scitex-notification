"""Tests for env-configured email profiles and send_with_profile."""

import email
import email.policy
import email.utils
import os
import shutil
import subprocess

import pytest

from scitex_notification import (
    MessageFormatError,
    Profile,
    ProfileError,
    get_profile,
    send_with_profile,
)
from scitex_notification._templates import NOTICE_RULE

P = "SCITEX_NOTIFICATION_PROFILE_OPS_"
ENV = {
    P + "FROM": "no-reply@example.org",
    P + "FROM_NAME": "Example Ops",
    P + "TO": "dev@example.org",
    P + "SMTP_HOST": "smtp.example.org",
    P + "SMTP_PORT": "2525",
    P + "PASSWORD": "local-test-only",
}

NOTICE_SUBJECT = "[SciTeX][alarm] FYI: disk 91% on /data"
NOTICE_BODY = (
    f"■ DONE\n  - alarm raised\n\n{NOTICE_RULE}\nagent: alarm | host: h1 | card/PR: -\n"
)


def _profile(port):
    return Profile(
        name="local",
        from_addr="no-reply@example.org",
        from_name="Example Ops",
        to="dev@example.org",
        smtp_host="127.0.0.1",
        smtp_port=port,
        password="local-test-only",
    )


def _problem(environ, name="ops"):
    try:
        get_profile(name, environ)
    except ProfileError as exc:
        return str(exc)
    return ""


def test_get_profile_reads_every_field():
    # Arrange
    environ = ENV
    # Act
    profile = get_profile("ops", environ)
    # Assert
    assert profile.describe() == {
        "profile": "ops",
        "from": "no-reply@example.org",
        "from_name": "Example Ops",
        "to": "dev@example.org",
        "smtp_host": "smtp.example.org",
        "smtp_port": 2525,
        "has_password": True,
    }


def test_profile_repr_hides_password():
    # Arrange
    profile = get_profile("ops", ENV)
    # Act
    text = repr(profile)
    # Assert
    assert "local-test-only" not in text


def test_profile_name_maps_dashes_to_underscores():
    # Arrange
    environ = {k.replace("_OPS_", "_OPS_ALARM_"): v for k, v in ENV.items()}
    # Act
    profile = get_profile("ops-alarm", environ)
    # Assert
    assert profile.to == "dev@example.org"


def test_missing_profile_names_each_missing_variable():
    # Arrange
    environ = {}
    # Act
    message = _problem(environ)
    # Assert
    assert all(P + s in message for s in ("FROM", "TO", "SMTP_HOST"))


def test_recipient_must_be_one_address():
    # Arrange
    environ = {**ENV, P + "TO": "a@example.org, b@example.org"}
    # Act
    message = _problem(environ)
    # Assert
    assert P + "TO is not a single email address" in message


def test_password_and_password_file_are_exclusive(tmp_path):
    # Arrange
    environ = {**ENV, P + "PASSWORD_FILE": str(tmp_path / "pw")}
    # Act
    message = _problem(environ)
    # Assert
    assert "set only one of" in message


def test_password_file_is_read_when_owner_only(tmp_path):
    # Arrange
    secret = tmp_path / "pw"
    secret.write_text("from-file\n")
    secret.chmod(0o600)
    environ = {k: v for k, v in ENV.items() if k != P + "PASSWORD"}
    environ[P + "PASSWORD_FILE"] = str(secret)
    # Act
    profile = get_profile("ops", environ)
    # Assert
    assert profile.password == "from-file"


def test_password_file_readable_by_others_is_refused(tmp_path):
    # Arrange
    secret = tmp_path / "pw"
    secret.write_text("from-file\n")
    secret.chmod(0o644)
    environ = {k: v for k, v in ENV.items() if k != P + "PASSWORD"}
    environ[P + "PASSWORD_FILE"] = str(secret)
    # Act
    message = _problem(environ)
    # Assert
    assert "chmod 600" in message


def test_get_profile_reads_os_environ_by_default():
    # Arrange
    os.environ.update({k.replace("_OPS_", "_ENVTEST_"): v for k, v in ENV.items()})
    try:
        # Act
        profile = get_profile("envtest")
    finally:
        for key in [k for k in os.environ if k.startswith(P.replace("OPS", "ENVTEST"))]:
            del os.environ[key]
    # Assert
    assert profile.from_addr == "no-reply@example.org"


def test_send_with_profile_validates_template_before_sending():
    # Arrange
    profile = _profile(1)  # nothing listens on port 1: validation must fail first
    call = lambda: send_with_profile(  # noqa: E731
        profile, "free text subject", "hello", template="notice", dry_run=True
    )
    # Act
    expected = MessageFormatError
    # Assert
    with pytest.raises(expected):
        call()


def test_send_with_profile_dry_run_reports_identity(tmp_path):
    # Arrange
    profile = _profile(1)
    # Act
    result = send_with_profile(
        profile,
        NOTICE_SUBJECT,
        NOTICE_BODY,
        template="notice",
        dedupe_key="disk:/data",
        dedupe_window_s=3600,
        rate_limit_dir=tmp_path,
        dry_run=True,
    )
    # Assert
    assert (result["status"], result["to"], result["from"], result["would_send"]) == (
        "dry_run",
        "dev@example.org",
        "no-reply@example.org",
        True,
    )


def test_dedupe_key_requires_a_window():
    # Arrange
    call = lambda: send_with_profile(  # noqa: E731
        _profile(1), "s", "b", dedupe_key="k", dry_run=True
    )
    # Act
    expected = ValueError
    # Assert
    with pytest.raises(expected):
        call()


def test_send_with_profile_delivers_as_the_profile(smtp_server):
    # Arrange
    profile = _profile(smtp_server.port)
    # Act
    result = send_with_profile(
        profile,
        NOTICE_SUBJECT,
        NOTICE_BODY,
        template="notice",
        ssl_context=smtp_server.client_context,
    )
    smtp_server.thread.join(timeout=10)
    record = smtp_server.record
    header = email.message_from_bytes(record["data"], policy=email.policy.default)
    # Assert
    assert (
        result["status"],
        record["login"],
        record["envelope_from"],
        record["envelope_to"],
        email.utils.getaddresses([str(header["From"])])[0],
        str(header["Subject"]),
    ) == (
        "sent",
        "no-reply@example.org",
        "<no-reply@example.org>",
        "<dev@example.org>",
        ("Example Ops", "no-reply@example.org"),
        NOTICE_SUBJECT,
    )


def test_send_with_profile_suppresses_a_repeat(smtp_server, tmp_path):
    # Arrange
    profile = _profile(smtp_server.port)
    kwargs = dict(
        ssl_context=smtp_server.client_context,
        dedupe_key="disk:/data",
        dedupe_window_s=3600,
        rate_limit_dir=tmp_path,
    )
    send_with_profile(profile, NOTICE_SUBJECT, NOTICE_BODY, **kwargs)
    smtp_server.thread.join(timeout=10)
    # Act
    second = send_with_profile(profile, NOTICE_SUBJECT, NOTICE_BODY, **kwargs)
    # Assert
    assert second["status"] == "suppressed"


def test_failed_send_is_not_recorded_for_dedupe(tmp_path):
    # Arrange
    profile = _profile(1)  # connection refused
    kwargs = dict(dedupe_key="k", dedupe_window_s=3600, rate_limit_dir=tmp_path)
    try:
        send_with_profile(profile, NOTICE_SUBJECT, NOTICE_BODY, **kwargs)
    except OSError:
        pass
    # Act
    result = send_with_profile(
        profile, NOTICE_SUBJECT, NOTICE_BODY, dry_run=True, **kwargs
    )
    # Assert
    assert result["would_send"] is True


def _gpg(home, *args, **kwargs):
    return subprocess.run(
        ["gpg", "--homedir", str(home), "--batch", *args],
        check=True,
        capture_output=True,
        timeout=60,
        **kwargs,
    )


def _gpg_keyring(tmp_path):
    """A throwaway passphrase-less gpg keyring; skip when gpg is absent."""
    if shutil.which("gpg") is None:
        pytest.skip("gpg not installed")
    home = tmp_path / "gnupg"
    home.mkdir(mode=0o700)
    _gpg(home, "--passphrase", "", "--quick-gen-key", "t@example.org", "ed25519")
    listing = _gpg(home, "--with-colons", "--list-keys", text=True).stdout
    fpr = next(ln.split(":")[9] for ln in listing.splitlines() if ln.startswith("fpr"))
    _gpg(home, "--passphrase", "", "--quick-add-key", fpr, "cv25519", "encr")
    return home


def _encrypt(home, tmp_path, plaintext):
    cipher = tmp_path / "pw.gpg"
    _gpg(
        home,
        "--yes",
        "--trust-model",
        "always",
        "-r",
        "t@example.org",
        "-o",
        str(cipher),
        "--encrypt",
        input=plaintext.encode(),
    )
    return cipher


def _gpg_environ(cipher, home):
    environ = {k: v for k, v in ENV.items() if k != P + "PASSWORD"}
    environ[P + "PASSWORD_GPG"] = str(cipher)
    environ[P + "GNUPGHOME"] = str(home)
    return environ


def test_password_gpg_is_decrypted_in_memory(tmp_path):
    # Arrange
    home = _gpg_keyring(tmp_path)
    environ = _gpg_environ(_encrypt(home, tmp_path, "from-gpg\n"), home)
    # Act
    profile = get_profile("ops", environ)
    # Assert
    assert profile.password == "from-gpg"


def test_password_gpg_without_the_key_names_the_variable(tmp_path):
    # Arrange
    home = _gpg_keyring(tmp_path)
    cipher = _encrypt(home, tmp_path, "from-gpg\n")
    empty_home = tmp_path / "empty-gnupg"
    empty_home.mkdir(mode=0o700)
    # Act
    message = _problem(_gpg_environ(cipher, empty_home))
    # Assert
    assert P + "PASSWORD_GPG: cannot decrypt" in message


def test_password_and_password_gpg_are_exclusive(tmp_path):
    # Arrange
    environ = {**ENV, P + "PASSWORD_GPG": str(tmp_path / "pw.gpg")}
    # Act
    message = _problem(environ)
    # Assert
    assert "set only one of" in message
