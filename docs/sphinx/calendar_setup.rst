Google Calendar Channel Setup
=============================

The calendar channel (``scitex-notification >= 0.4.0``) records
**milestones**, such as a release published, a PR merged or a result
verified, as Google Calendar events. It calls the Google Calendar API
directly, using only the Python standard library, so it needs no extra
dependency and no browser after the one-time setup below.

Every entry follows these rules, and the package enforces them:

* zero duration (start equals end), **Free**, **Private**, reminders off
* the calendar's colour if it is SciTeX navy ``#1E293B``, else event colour ``9``
* no duplicates: the same title at the same second in the same calendar
  returns ``status: "exists"`` and writes nothing
* every new entry is read back and verified; a broken rule raises ``CalendarError``
* the authorized token must belong to ``SCITEX_NOTIFICATION_GCAL_ACCOUNT``

The setup takes about 10 minutes. Placeholders: ``<account>`` is the Google
account that writes the entries, ``<host>`` is the machine that runs
``scitex-notification``, and ``<laptop>`` is the machine with the browser.

.. contents::
   :local:
   :depth: 1

1. Google Cloud side
--------------------

Do these steps once, signed in to the Google Cloud console as the owner of
a project. Any project works. A project that Gemini / AI Studio created
automatically also works, but its consent screen then shows that project's
app name.

1. **Enable the Calendar API**:
   ``https://console.cloud.google.com/apis/library/calendar-json.googleapis.com?project=<project-id>``.
   Append ``?project=<project-id>`` to every console URL. The project
   selector does not always switch the project.
2. **Audience** (``https://console.cloud.google.com/auth/audience?project=<project-id>``):

   * Google Workspace account: choose user type **Internal**. Its tokens do
     not expire.
   * Personal or non-Workspace account: choose user type **External**. While
     the publishing status is **Testing**, add ``<account>`` under
     **Test users**. If you skip this, the consent page shows *"Access
     blocked: <app> has not completed the Google verification process"*
     (*Error 403: access_denied*).

3. **Client** (``https://console.cloud.google.com/auth/clients?project=<project-id>``):
   choose **Create client**, set the type to **Desktop app**, give it a
   name, and choose **Download JSON**. A *Web application* client does not
   work.

The channel requests the two narrowest scopes that work:
``calendar.calendarlist.readonly``, to verify the account and find
calendars, and ``calendar.events``.

.. warning::

   **Testing mode expires tokens after about 7 days.** Google expires the
   refresh token of an External app in *Testing* status after about 7
   days. Writes then fail with ``invalid_grant``. Re-run
   `3. Authorize`_ to get a new token. To stop the expiry, finish
   **Branding** and **Publish app** on the Audience page, or use an
   **Internal** app on Google Workspace.

2. Host side
------------

On ``<host>``:

.. code-block:: bash

   # install (0.4.0+ has the calendar channel; no extra needed)
   uv pip install "scitex-notification>=0.4.0"

   # store the downloaded client JSON with private permissions
   mkdir -p ~/.scitex/notification/secrets
   chmod 700 ~/.scitex/notification/secrets
   cp ~/Downloads/client_secret_*.json ~/.scitex/notification/secrets/gcal-client.json
   chmod 600 ~/.scitex/notification/secrets/gcal-client.json

   # the account the entries must be written as
   export SCITEX_NOTIFICATION_GCAL_ACCOUNT=<account>

If the JSON was downloaded on ``<laptop>``, copy it with ``scp`` and apply
the ``chmod`` on ``<host>``. Never paste the file's contents into chat,
issues or logs.

.. list-table:: Environment variables
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Meaning
   * - ``SCITEX_NOTIFICATION_GCAL_ACCOUNT``
     - Required. The account the entries must be written as.
   * - ``SCITEX_NOTIFICATION_GCAL_CLIENT_FILE``
     - Desktop-app client JSON. Default
       ``$SCITEX_DIR/notification/secrets/gcal-client.json``
       (``$SCITEX_DIR`` defaults to ``~/.scitex``).
   * - ``SCITEX_NOTIFICATION_GCAL_TOKEN_FILE``
     - Refresh token written by ``calendar authorize``. Default
       ``$SCITEX_DIR/notification/secrets/gcal-token.json``.

Both files must be regular files, owned by the current user, and not
readable by group or others (mode ``0600``). If you keep the secrets
directory inside a dotfiles repository, make sure the repository ignores it
and check with ``git check-ignore``.

3. Authorize
------------

On ``<host>``:

.. code-block:: bash

   scitex-notification calendar authorize --dry-run      # checks the client file only
   scitex-notification calendar authorize --port 8765 --timeout 900

The command prints a Google URL and waits on ``127.0.0.1:8765``. After you
give consent, Google redirects the browser to that address, so the browser
must reach port 8765 on ``<host>``. If the browser runs on another machine,
use either tunnel:

* **Forward tunnel, started on <laptop>:**

  .. code-block:: bash

     ssh -N -L 8765:127.0.0.1:8765 <host>

* **Reverse tunnel, started on <host>.** Use this when ``<host>`` can reach
  ``<laptop>`` but not the other way round:

  .. code-block:: bash

     ssh -N -R 8765:127.0.0.1:8765 <user>@<laptop>

Then:

1. Open the URL in a browser signed in as ``<account>``.
2. For an unverified Testing app, choose **Continue**, then **Allow** both
   permissions.
3. The browser shows *"scitex-notification: calendar authorized; close this
   tab."* The token file appears with mode 0600. The package saves it only
   after the calendar list proves the token belongs to ``<account>``.
4. Stop the tunnel by its PID (``pgrep -af 'ssh -N'``, then ``kill <pid>``).
   A broad ``pkill -f`` pattern can match, and kill, the shell that runs it.

Check the result:

.. code-block:: bash

   scitex-notification calendar list-calendars

This lists every calendar that ``<account>`` sees, with its ``access_role``.
Each calendar you write to needs ``writer`` or ``owner``.

4. Record milestones
--------------------

.. code-block:: bash

   # event body only, no network
   scitex-notification calendar add-milestone -c "<Calendar name>" \
       -t "<short title>" --at 2026-01-01T09:00:00+09:00 \
       -n "Outcome. <source link>" --offline

   # every check (account, calendar, duplicate) read-only
   scitex-notification calendar add-milestone ... --dry-run

   # write it (status created | exists, event_id, html_link)
   scitex-notification calendar add-milestone ...

The time must carry an offset (``+09:00`` or ``Z``). Use the authoritative
time: the registry upload time for a publication, the PR merge time for a
merge, the run record for a verification.

To record a batch, loop over a JSON list of ``{calendar, title, at, note}``
in Python, first with ``dry_run=True``:

.. code-block:: python

   import json
   import scitex_notification as stxn

   for item in json.load(open("milestones.json", encoding="utf-8")):
       print(stxn.add_milestone(item["calendar"], item["title"], item["at"],
                                item["note"], dry_run=True))

Exit codes: ``0`` ok, ``1`` credential / account / API failure, ``2``
invalid milestone.

5. Troubleshooting
------------------

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Symptom
     - Cause
     - Fix
   * - ``invalid_grant`` on writes
     - Testing-mode token expired (~7 days) or revoked
     - Re-run `3. Authorize`_. Publish the app or use Internal to stop it.
   * - "Access blocked ... Error 403: access_denied"
     - Account is not a test user of the Testing app
     - Add ``<account>`` under Audience, Test users
   * - ``SCITEX_NOTIFICATION_GCAL_ACCOUNT is not set``
     - Missing environment variable
     - ``export SCITEX_NOTIFICATION_GCAL_ACCOUNT=<account>``
   * - ``must not be readable by group/others``
     - File mode too open
     - ``chmod 600`` the client and token files
   * - ``is not a Google 'Desktop app' OAuth client``
     - Wrong client type (e.g. Web application)
     - Create a **Desktop app** client and download it again
   * - ``authorized for '<x>', not '<account>'``
     - Consent was given in a different Google account
     - Re-authorize while signed in as ``<account>``
   * - ``consent did not grant ...``
     - A permission was left unticked
     - Re-authorize and allow both permissions
   * - ``Google returned no refresh_token``
     - Google reused an earlier grant
     - Remove the app at ``https://myaccount.google.com/permissions``, then re-authorize
   * - Browser cannot reach ``127.0.0.1:8765``; authorize times out
     - No tunnel, or the tunnel points at the wrong host
     - Start one of the tunnels above; re-run with ``--timeout 900``
   * - ``No such command 'calendar'``
     - scitex-notification below 0.4.0
     - Upgrade, or use a dedicated venv with ``>=0.4.0``
   * - Calendar not found or ambiguous
     - The name does not match exactly one calendar
     - Run ``list-calendars`` and copy the exact name
   * - ``status: "exists"``
     - Same title at the same second already recorded
     - Nothing to do; dedupe worked
