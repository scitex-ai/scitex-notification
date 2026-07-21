Environment Variables
=====================

General
-------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Description
   * - ``SCITEX_NOTIFICATION_DEFAULT_BACKEND``
     - Default notification backend (default: ``audio``)
   * - ``SCITEX_NOTIFICATION_ENV_SRC``
     - Path to .env file to auto-load on import

Email
-----

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Description
   * - ``SCITEX_NOTIFICATION_EMAIL_HOST``
     - SMTP server hostname
   * - ``SCITEX_NOTIFICATION_EMAIL_PORT``
     - SMTP server port
   * - ``SCITEX_NOTIFICATION_EMAIL_USER``
     - SMTP username
   * - ``SCITEX_NOTIFICATION_EMAIL_PASS``
     - SMTP password or app password
   * - ``SCITEX_NOTIFICATION_EMAIL_TO``
     - Recipient email address
   * - ``SCITEX_NOTIFICATION_EMAIL_FROM``
     - Sender email address (optional)

Twilio
------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Description
   * - ``SCITEX_NOTIFICATION_TWILIO_SID``
     - Twilio Account SID
   * - ``SCITEX_NOTIFICATION_TWILIO_TOKEN``
     - Twilio Auth Token
   * - ``SCITEX_NOTIFICATION_TWILIO_FROM``
     - Twilio phone number
   * - ``SCITEX_NOTIFICATION_TWILIO_TO``
     - Destination phone number

Telegram
--------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Description
   * - ``SCITEX_NOTIFICATION_TELEGRAM_BOT_TOKEN``
     - Telegram Bot API token
   * - ``SCITEX_NOTIFICATION_TELEGRAM_CHAT_ID``
     - Target chat ID

Webhook
-------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Description
   * - ``SCITEX_NOTIFICATION_WEBHOOK_URL``
     - Webhook endpoint URL

Playwright
----------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Description
   * - ``SCITEX_NOTIFICATION_PLAYWRIGHT_HEADLESS``
     - Run headless (true/false)
