SciTeX Notification
===================

.. raw:: html

   <p align="center"><b>Multi-backend notification system for scientific workflows</b></p>
   <br>

**SciTeX Notification** provides a unified interface for sending notifications
across multiple backends, allowing you to stay informed about long-running
scientific computations wherever you are.

Supported Backends
------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 15 15 30

   * - Backend
     - Transport
     - Cost
     - Internet
     - Notes
   * - **Audio**
     - Local audio alert
     - Free
     - No
     - Requires scitex-audio
   * - **SMS (Twilio)**
     - SMS text message
     - Paid
     - Required
     - Requires Twilio account
   * - **Email**
     - SMTP email
     - Free
     - Required
     - Supports Gmail, SMTP relay
   * - **Webhook**
     - HTTP POST
     - Free
     - Required
     - Slack, Discord, custom endpoints

Quick Example
-------------

.. code-block:: python

   import scitex_notification as notify

   # Send via default backend
   notify.send("Training complete. Val loss: 0.042")

   # Send via specific backend
   notify.send("Job finished", backend="email")

   # Notify on function completion
   @notify.on_complete(backend="audio")
   def train_model():
       ...  # long-running computation

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
