Quickstart
==========

Installation
------------

.. code-block:: bash

   pip install scitex-notification

Optional backend dependencies:

.. code-block:: bash

   pip install scitex-notification[audio]   # Audio backend (scitex-audio)
   pip install scitex-notification[twilio]  # Twilio phone/SMS
   pip install scitex-notification[email]   # Email
   pip install scitex-notification[playwright]  # Browser popup
   pip install scitex-notification[matplotlib]  # Visual popup
   pip install scitex-notification[mcp]     # MCP server
   pip install scitex-notification[all]     # Everything

Basic Usage
-----------

.. code-block:: python

   import scitex_notification as stxn

   # Send a simple alert (auto-fallback across available backends)
   stxn.alert("Training complete. Val loss: 0.042")

   # Specify a backend
   stxn.alert("Job finished", backend="email")

   # Phone call for critical alerts
   stxn.call("Server is down — wake up!")

   # SMS
   stxn.sms("Build done!")

Async Usage
-----------

.. code-block:: python

   import asyncio
   import scitex_notification as stxn

   async def main():
       await stxn.alert_async("Async alert", backend="desktop")
       await stxn.call_async("Critical async alert")
       await stxn.sms_async("Build done!")

   asyncio.run(main())
