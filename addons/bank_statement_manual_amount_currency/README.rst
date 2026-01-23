Bank Statement Manual Amount Currency
=====================================

This module exposes the ``amount_currency`` and ``foreign_currency_id`` fields on
bank statement lines so users can set per-transaction amounts in a foreign
currency. The computed value is only filled when empty, so manual values remain
locked in place after import or reconciliation. The fields are injected into the
standard list/form views so reconciliation UIs that reuse those views can also
access them.

It also logs when a manual foreign amount is provided without a foreign
currency to assist with troubleshooting.
