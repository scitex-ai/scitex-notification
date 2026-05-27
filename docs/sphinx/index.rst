SciTeX Notification
===================

.. raw:: html

   <p align="center"><b>One-call alerting across 9 backends — audio, desktop, emacs, matplotlib, playwright, email, webhook, Telegram, Twilio.</b></p>
   <br>

**SciTeX Notification** provides a unified alerting interface across 9 backends
with automatic fallback. Perfect for long-running scientific computations, AI
agents, and any workflow that needs your attention — even while you sleep.

Backends
--------

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

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   quickstart
   backends
   configuration
   env_vars

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/scitex_notification
   api/backends
   api/mcp

Quick Examples
--------------

.. code-block:: python

   import scitex_notification as stxn

   # Simple alert — fallback: audio → emacs → matplotlib → playwright → email
   stxn.alert("Training complete. Val loss: 0.042")

   # Specific backend
   stxn.alert("Job finished", backend="email")

   # Escalate to phone call
   stxn.call("Server is down — wake up!")

   # Send SMS
   stxn.sms("Build done!")

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
