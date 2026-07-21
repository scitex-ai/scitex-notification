Configuration
=============

Default Backend
---------------

Set the default notification backend via environment variable:

.. code-block:: bash

   export SCITEX_NOTIFICATION_DEFAULT_BACKEND=email

If unset, ``audio`` is used as the default.

Per-Backend Configuration
-------------------------

Each backend may require additional environment variables or configuration.
See the specific backend documentation for details.

Email
~~~~~

.. code-block:: bash

   export SCITEX_NOTIFICATION_EMAIL_HOST=smtp.gmail.com
   export SCITEX_NOTIFICATION_EMAIL_PORT=587
   export SCITEX_NOTIFICATION_EMAIL_USER=your@gmail.com
   export SCITEX_NOTIFICATION_EMAIL_PASS=app-password
   export SCITEX_NOTIFICATION_EMAIL_TO=recipient@example.com

Twilio
~~~~~~

.. code-block:: bash

   export SCITEX_NOTIFICATION_TWILIO_SID=your_account_sid
   export SCITEX_NOTIFICATION_TWILIO_TOKEN=your_auth_token
   export SCITEX_NOTIFICATION_TWILIO_FROM=+1234567890
   export SCITEX_NOTIFICATION_TWILIO_TO=+0987654321

Telegram
~~~~~~~~

.. code-block:: bash

   export SCITEX_NOTIFICATION_TELEGRAM_BOT_TOKEN=your_bot_token
   export SCITEX_NOTIFICATION_TELEGRAM_CHAT_ID=your_chat_id

Webhook
~~~~~~~

.. code-block:: bash

   export SCITEX_NOTIFICATION_WEBHOOK_URL=https://hooks.example.com/notify

Programmatic Use
----------------

.. code-block:: python

   import scitex_notification as stxn

   # List available backends
   available = stxn.available_backends()
