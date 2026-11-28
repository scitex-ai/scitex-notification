#!/usr/bin/env python3
# File: src/scitex_notification/_calendar/_client.py

"""A minimal Google Calendar v3 client on the standard library."""

from __future__ import annotations

import datetime as _dt
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping, Optional

from ._credentials import CalendarCredentials
from ._rules import CalendarError

API = "https://www.googleapis.com/calendar/v3"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def request_json(
    method: str,
    url: str,
    *,
    token: Optional[str] = None,
    body: Optional[Mapping[str, Any]] = None,
    form: Optional[Mapping[str, str]] = None,
) -> dict:
    """One HTTPS call; an HTTP error is a :class:`CalendarError` (no secrets)."""
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(dict(body)).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(dict(form)).encode("ascii")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    path = urllib.parse.urlsplit(url).path
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            payload = json.loads(exc.read() or b"{}")
            err = payload.get("error")
            if isinstance(err, dict):
                detail = err.get("message", "")
            elif err:
                detail = f"{err} {payload.get('error_description', '')}".strip()
        except ValueError:
            pass
        raise CalendarError(f"{method} {path} failed: HTTP {exc.code} {detail}".strip())
    except urllib.error.URLError as exc:
        raise CalendarError(f"{method} {path} failed: {exc.reason}")
    return json.loads(raw) if raw else {}


class GoogleCalendarClient:
    """Calendar v3 calls authorized by the credential's refresh token."""

    def __init__(
        self, credentials: CalendarCredentials, access_token: Optional[str] = None
    ):
        self.credentials = credentials
        self._access_token = access_token

    def _token(self) -> str:
        if self._access_token is None:
            c = self.credentials
            reply = request_json(
                "POST",
                TOKEN_URI,
                form={
                    "client_id": c.client_id,
                    "client_secret": c.client_secret,
                    "refresh_token": c.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            self._access_token = reply.get("access_token")
            if not self._access_token:
                raise CalendarError("token refresh returned no access_token")
        return self._access_token

    def _get(self, path: str, **params) -> dict:
        query = urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None}
        )
        url = f"{API}{path}" + (f"?{query}" if query else "")
        return request_json("GET", url, token=self._token())

    @staticmethod
    def _quote(value: str) -> str:
        return urllib.parse.quote(value, safe="")

    def calendar_list(self) -> list:
        """Every calendarList entry of the authorized account."""
        items, page = [], None
        while True:
            reply = self._get("/users/me/calendarList", pageToken=page, maxResults=250)
            items.extend(reply.get("items", []))
            page = reply.get("nextPageToken")
            if not page:
                return items

    def events_between(
        self, calendar_id: str, start: _dt.datetime, end: _dt.datetime
    ) -> list:
        """Events overlapping [start, end), recurring ones expanded."""
        items, page = [], None
        while True:
            reply = self._get(
                f"/calendars/{self._quote(calendar_id)}/events",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents="true",
                showDeleted="false",
                maxResults=250,
                pageToken=page,
            )
            items.extend(reply.get("items", []))
            page = reply.get("nextPageToken")
            if not page:
                return items

    def insert_event(self, calendar_id: str, event: Mapping[str, Any]) -> dict:
        url = f"{API}/calendars/{self._quote(calendar_id)}/events"
        return request_json("POST", url, token=self._token(), body=event)

    def get_event(self, calendar_id: str, event_id: str) -> dict:
        return self._get(
            f"/calendars/{self._quote(calendar_id)}/events/{self._quote(event_id)}"
        )


# EOF
