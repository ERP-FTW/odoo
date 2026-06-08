Account Payment Outbound Base
=============================

MVP base module to send posted outbound supplier ``account.payment`` records to a configured ``payment.provider`` and track execution on ``payment.transaction``.

Flow
----
1. Create/post vendor payment in standard Odoo flow.
2. Click **Send Outbound Payment** on payment form.
3. Module creates/reuses outbound ``payment.transaction`` and calls provider send hook.
4. Click **Refresh Outbound Status** to poll provider-side status.
