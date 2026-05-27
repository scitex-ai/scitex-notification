Backends
========

SciTeX Notification supports 9 backends. Backends are tried in fallback
priority order when none is specified.

Available Backends
------------------

.. list-table::
   :header-rows: 1
   :widths: 15 20 10 10 45

   * - Backend
     - Transport
     - Cost
     - Internet
     - Notes
   * - **Audio**
     - TTS to local speakers
     - Free
     - No
     - Via scitex-audio; SSH relay supported
   * - **Desktop**
     - ``notify-send`` / PowerShell
     - Free
     - No
     - Linux / WSL
   * - **Emacs**
     - ``emacsclient`` popup
     - Free
     - No
     - Popup, minibuffer, or alert
   * - **Matplotlib**
     - Visual popup window
     - Free
     - No
     - Requires ``matplotlib``
   * - **Playwright**
     - Browser popup
     - Free
     - No
     - Requires ``playwright``
   * - **Email**
     - SMTP
     - Free
     - Required
     - Gmail, SMTP relay
   * - **Webhook**
     - HTTP POST
     - Free
     - Required
     - Slack, Discord, custom endpoints
   * - **Telegram**
     - Telegram Bot API
     - Free
     - Required
     - No SDK dependency (urllib only)
   * - **Twilio**
     - Phone call / SMS
     - Paid
     - Required
     - Twilio account needed; no SDK dependency

Fallback Priority
-----------------

When no backend is specified, the default fallback order is:

1. **audio** — TTS (fast, non-blocking)
2. **emacs** — Minibuffer message (if in Emacs)
3. **matplotlib** — Visual popup
4. **playwright** — Browser popup
5. **email** — Email (slowest, most reliable)

Set ``fallback=False`` to disable fallback behavior.
