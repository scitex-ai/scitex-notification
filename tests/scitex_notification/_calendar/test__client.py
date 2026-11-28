"""HTTP error handling against a real local server (no mocks)."""

import http.server
import json
import threading

import pytest

from scitex_notification import CalendarError
from scitex_notification._calendar._client import request_json


class _Forbidden(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = json.dumps({"error": {"message": "Insufficient Permission"}})
        self.send_response(403)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *_):
        pass


@pytest.fixture
def forbidden_url():
    server = http.server.HTTPServer(("127.0.0.1", 0), _Forbidden)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/calendar/v3/x"
    thread.join(5)
    server.server_close()


def test_http_error_becomes_calendar_error_with_google_message(forbidden_url):
    # Arrange
    url = forbidden_url
    # Act
    call = lambda: request_json("GET", url, token="local-only")  # noqa: E731
    # Assert
    with pytest.raises(CalendarError, match="HTTP 403 Insufficient Permission"):
        call()
