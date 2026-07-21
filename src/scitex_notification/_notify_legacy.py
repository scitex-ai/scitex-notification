#!/usr/bin/env python3
# Timestamp: "2026-05-30 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-notification/src/scitex_notification/_notify_legacy.py

"""Legacy ``notify`` / ``send_gmail`` helpers migrated from the scitex umbrella.

These functions provide the richer, script-aware email notification API that
used to live in ``scitex.utils._notify`` / ``scitex.utils._email``:

- :func:`notify` — send a script-aware notification email with an
  auto-generated footer (host, script name, package version, git branch).
- :func:`send_gmail` — low-level SMTP sender supporting CC, attachments and an
  optional message ID. Despite the name, it works with any SMTP server and
  auto-detects the server from the sender address.

They are self-contained (stdlib only) and intentionally distinct from the
``alert(backend="email")`` notification backend, which targets short alerts
rather than full script-completion reports.
"""

from __future__ import annotations

import inspect
import mimetypes
import os
import re
import smtplib
import socket
import subprocess
import sys
import warnings
from email import encoders
from email.mime.base import MIMEBase as _MIMEBase
from email.mime.multipart import MIMEMultipart as _MIMEMultipart
from email.mime.text import MIMEText as _MIMEText
from typing import Optional, Union

ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _gen_id(n: int = 8) -> str:
    """Generate a short random alphanumeric ID (stdlib only)."""
    import random
    import string

    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def get_username() -> str:
    """Return the current username, falling back to env vars."""
    try:
        import pwd

        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return os.getenv("USER") or os.getenv("LOGNAME") or "unknown"


def get_hostname() -> str:
    """Return the local hostname."""
    return socket.gethostname()


def get_git_branch(package) -> str:
    """Return the current git branch of ``package``'s source tree.

    Parameters
    ----------
    package : module
        A module exposing ``__path__`` (e.g. ``scitex_notification``).
    """
    try:
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=package.__path__[0],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        return branch
    except Exception as e:
        print(e)
        return "main"


def gen_footer(sender: str, script_name: str, package, branch: str) -> str:
    """Build the notification footer block.

    Parameters
    ----------
    sender : str
        ``user@host`` identifier of the sender.
    script_name : str
        Name of the script that triggered the notification.
    package : module
        Module exposing ``__version__`` (used in the footer).
    branch : str
        Git branch name to reference.
    """
    version = getattr(package, "__version__", "unknown")
    return f"""

{"-" * 30}
Sent via
- Host: {sender}
- Script: {script_name}
- Source: scitex-notification v{version}
{"-" * 30}"""


def send_gmail(
    sender_gmail: str,
    sender_password: str,
    recipient_email: str,
    subject: str,
    message: str,
    sender_name: Optional[str] = None,
    cc: Optional[Union[str, list]] = None,
    ID: Optional[str] = None,
    attachment_paths: Optional[list] = None,
    verbose: bool = True,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
) -> None:
    """Send an email via SMTP.

    Despite the name, supports any SMTP server. Uses
    ``mail1030.onamae.ne.jp`` by default (for scitex.ai emails) and falls back
    to Gmail's server when the sender address ends in ``@gmail.com``.

    Parameters
    ----------
    sender_gmail : str
        Sender email address (and SMTP login).
    sender_password : str
        SMTP password.
    recipient_email : str
        Primary recipient address.
    subject : str
        Email subject. If ``ID`` is given it is appended as ``(ID: ...)``.
    message : str
        Plain-text body.
    sender_name : str, optional
        Display name for the ``From`` header.
    cc : str or list, optional
        CC recipient(s).
    ID : str, optional
        Message ID. Pass ``"auto"`` to auto-generate one.
    attachment_paths : list, optional
        Paths of files to attach. ``.log`` files are ANSI-stripped.
    verbose : bool
        Print a confirmation line on success.
    smtp_server, smtp_port : optional
        Override SMTP host/port auto-detection.
    """
    if ID == "auto":
        ID = _gen_id()

    if ID:
        if subject:
            subject = f"{subject} (ID: {ID})"
        else:
            subject = f"ID: {ID}"

    # Auto-detect SMTP server based on sender email or use provided server
    if smtp_server is None:
        if "@gmail.com" in sender_gmail:
            smtp_server = "smtp.gmail.com"
            smtp_port = smtp_port or 587
        else:
            # Use scitex.ai mail server for scitex.ai emails
            smtp_server = os.getenv(
                "SCITEX_SCHOLAR_FROM_EMAIL_SMTP_SERVER", "mail1030.onamae.ne.jp"
            )
            smtp_port = smtp_port or int(
                os.getenv("SCITEX_SCHOLAR_FROM_EMAIL_SMTP_PORT", "587")
            )

    smtp_port = smtp_port or 587

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_gmail, sender_password)

        gmail = _MIMEMultipart()
        gmail["Subject"] = subject
        gmail["To"] = recipient_email
        if cc:
            if isinstance(cc, str):
                gmail["Cc"] = cc
            elif isinstance(cc, list):
                gmail["Cc"] = ", ".join(cc)
        if sender_name:
            gmail["From"] = f"{sender_name} <{sender_gmail}>"
        else:
            gmail["From"] = sender_gmail
        gmail_body = _MIMEText(message, "plain")
        gmail.attach(gmail_body)

        # Attachment files
        if attachment_paths:
            for path in attachment_paths:
                _, ext = os.path.splitext(path)
                if ext.lower() == ".log":
                    with open(path, encoding="utf-8") as file:
                        content = file.read()
                        cleaned_content = ansi_escape.sub("", content)
                        part = _MIMEText(cleaned_content, "plain")
                else:
                    mime_type, _ = mimetypes.guess_type(path)
                    if mime_type is None:
                        mime_type = "text/plain"
                    main_type, sub_type = mime_type.split("/", 1)
                    with open(path, "rb") as file:
                        part = _MIMEBase(main_type, sub_type)
                        part.set_payload(file.read())
                        encoders.encode_base64(part)

                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(path)}",
                )
                gmail.attach(part)

        recipients = [recipient_email]
        if cc:
            if isinstance(cc, str):
                recipients.append(cc)
            elif isinstance(cc, list):
                recipients.extend(cc)
        server.send_message(gmail, to_addrs=recipients)

        server.quit()

        if verbose:
            cc_info = f" (CC: {cc})" if cc else ""
            out = "Email was sent:\n"
            out += f"    {sender_gmail} -> {recipient_email}{cc_info}\n"
            out += f"    (ID: {ID})\n"
            if attachment_paths:
                out += "    Attached:\n"
                for ap in attachment_paths:
                    out += f"        {ap}\n"
            print(out)

    except Exception as e:
        print(f"Email was not sent: {e}")


# This is an automated system notification. If received outside working hours,
# please disregard.
def notify(
    subject: str = "",
    message: str = ":)",
    file: Optional[str] = None,
    ID: str = "auto",
    sender_name: Optional[str] = None,
    recipient_email: Optional[str] = None,
    cc: Optional[Union[str, list]] = None,
    attachment_paths: Optional[list] = None,
    verbose: bool = False,
) -> None:
    """Send a script-aware notification email.

    Builds a subject/body from the calling script's name and appends a footer
    with host, script, package version and git branch, then delegates to
    :func:`send_gmail`.

    Credentials and recipient are read from environment variables (with
    backward-compatible aliases):

    - sender: ``SCITEX_SCHOLAR_EMAIL_NOREPLY`` /
      ``SCITEX_SCHOLAR_FROM_EMAIL_ADDRESS`` / ``SCITEX_EMAIL_NOREPLY`` /
      ``SCITEX_EMAIL_AGENT`` (default ``no-reply@scitex.ai``)
    - password: ``SCITEX_SCHOLAR_EMAIL_PASSWORD`` /
      ``SCITEX_SCHOLAR_FROM_EMAIL_PASSWORD`` / ``SCITEX_EMAIL_PASSWORD``
    - recipient: ``SCITEX_SCHOLAR_EMAIL_RECIPIENT`` /
      ``SCITEX_SCHOLAR_TO_EMAIL_ADDRESS`` (or pass ``recipient_email=``)
    """
    import scitex_notification as _pkg

    try:
        message = str(message)
    except Exception as e:
        warnings.warn(str(e))

    FAKE_PYTHON_SCRIPT_NAME = "$ python -c ..."
    sender_gmail = os.getenv(
        "SCITEX_SCHOLAR_EMAIL_NOREPLY",
        os.getenv(
            "SCITEX_SCHOLAR_FROM_EMAIL_ADDRESS",
            os.getenv(
                "SCITEX_EMAIL_NOREPLY",
                os.getenv("SCITEX_EMAIL_AGENT", "no-reply@scitex.ai"),
            ),
        ),
    )
    sender_password = os.getenv(
        "SCITEX_SCHOLAR_EMAIL_PASSWORD",
        os.getenv(
            "SCITEX_SCHOLAR_FROM_EMAIL_PASSWORD",
            os.getenv("SCITEX_EMAIL_PASSWORD", ""),
        ),
    )
    recipient_email = recipient_email or os.getenv(
        "SCITEX_SCHOLAR_EMAIL_RECIPIENT",
        os.getenv("SCITEX_SCHOLAR_TO_EMAIL_ADDRESS", ""),
    )

    if file is not None:
        script_name = str(file)
    else:
        if sys.argv[0]:
            script_name = os.path.basename(sys.argv[0])
        else:
            frames = inspect.stack()
            script_name = (
                os.path.basename(frames[-1].filename) if frames else "(Not found)"
            )
        if (script_name == "-c") or (not script_name.endswith(".py")):
            script_name = FAKE_PYTHON_SCRIPT_NAME

    sender = f"{get_username()}@{get_hostname()}"
    branch = get_git_branch(_pkg)
    footer = gen_footer(sender, script_name, _pkg, branch)

    full_message = script_name + "\n\n" + message + "\n\n" + footer
    full_subject = (
        f"{script_name}—{subject}"
        if subject and (script_name != FAKE_PYTHON_SCRIPT_NAME)
        else f"{subject}"
    )

    if sender_gmail is None or sender_password is None:
        print(
            f"""
        Please set environmental variables to use this function ({inspect.stack()[0][3]}):\n\n
        $ export SCITEX_SCHOLAR_FROM_EMAIL_ADDRESS="agent@scitex.ai"
        $ export SCITEX_SCHOLAR_FROM_EMAIL_PASSWORD="YOUR_EMAIL_PASSWORD"
        $ export SCITEX_SCHOLAR_TO_EMAIL_ADDRESS="YOUR_EMAIL_ADDRESS"

        Or alternatively:
        $ export SCITEX_EMAIL_AGENT="agent@scitex.ai"
        $ export SCITEX_EMAIL_PASSWORD="YOUR_EMAIL_PASSWORD"
        """
        )

    send_gmail(
        sender_gmail,
        sender_password,
        recipient_email,
        full_subject,
        full_message,
        sender_name=sender_name,
        cc=cc,
        ID=ID,
        attachment_paths=attachment_paths,
        verbose=verbose,
    )


# EOF
