"""Shared fixtures: a real local SMTP server (STARTTLS + AUTH PLAIN)."""

import base64
import shutil
import socket
import ssl
import subprocess
import threading

import pytest


class _LocalSMTPServer:
    """Minimal real SMTP server on 127.0.0.1 that records one session."""

    def __init__(self, certfile, keyfile):
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.load_cert_chain(certfile, keyfile)
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.port = self.listener.getsockname()[1]
        self.listener.settimeout(15)
        self.record = {}
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        try:
            self._session()
        except (OSError, ssl.SSLError) as exc:  # e.g. the client refused our cert
            self.record["error"] = type(exc).__name__
        finally:
            self.listener.close()

    def _session(self):
        conn, _ = self.listener.accept()
        conn.settimeout(10)
        stream = conn.makefile("rb")

        def reply(text):
            conn.sendall(text.encode() + b"\r\n")

        reply("220 localhost ESMTP")
        while True:
            line = stream.readline().decode().rstrip("\r\n")
            verb = line.split(" ", 1)[0].upper()
            if verb in ("EHLO", "HELO"):
                reply("250-localhost\r\n250-AUTH PLAIN\r\n250 STARTTLS")
            elif verb == "STARTTLS":
                reply("220 ready")
                conn = self.context.wrap_socket(conn, server_side=True)
                stream = conn.makefile("rb")
                self.record["tls"] = True
            elif verb == "AUTH":
                token = line.split()[2]
                self.record["login"] = base64.b64decode(token).split(b"\0")[1].decode()
                reply("235 ok")
            elif verb == "MAIL":
                self.record["envelope_from"] = line.split(":", 1)[1].split()[0]
                reply("250 ok")
            elif verb == "RCPT":
                self.record["envelope_to"] = line.split(":", 1)[1].strip()
                self.record.setdefault("envelope_to_all", []).append(
                    self.record["envelope_to"]
                )
                reply("250 ok")
            elif verb == "DATA":
                reply("354 go")
                data = b""
                while not data.endswith(b"\r\n.\r\n"):
                    data += stream.readline()
                self.record["data"] = data[:-5]
                reply("250 queued")
            elif verb == "QUIT" or not line:
                reply("221 bye")
                break
            else:
                reply("250 ok")
        conn.close()


@pytest.fixture
def smtp_server(tmp_path):
    if shutil.which("openssl") is None:
        pytest.skip("openssl is needed to make the local server's TLS certificate")
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
         "-subj", "/CN=localhost", "-addext", "subjectAltName=IP:127.0.0.1,DNS:localhost", "-keyout", str(key), "-out", str(cert)],
        check=True,
        capture_output=True,
    )
    server = _LocalSMTPServer(str(cert), str(key))
    # Clients trust exactly this throwaway CA; verification stays on.
    server.client_context = ssl.create_default_context(cafile=str(cert))
    yield server
    server.thread.join(timeout=10)


