Inactive Customer Reporting
==========================

This addon extends **Sales Analysis** (model ``sale.report``) with a new field:

- **Last Order Date** (``partner_last_order_date``)

The field is computed in the SQL view as an aggregate and represents the latest
``sale.order.date_order`` (converted to date) for orders in states **sale** and
**done**.

Usage
-----

1. Install the module ``inactive_customer_reporting``.
2. Open **Sales > Reporting > Sales**.
3. In Pivot view:

   - Add measure **Last Order Date**.
   - Group by **Customer** to see each customer's most recent confirmed order date.
   - Optional group by **Last Order Date** (day/month/quarter/year) from the search panel.

4. In Search filters, use **Inactive 90+ days** to find report rows where
   ``partner_last_order_date`` is older than 90 days.

Troubleshooting
---------------

- **Field not visible in measures/group by:**

  - Upgrade the module (Apps > Update Apps List, then upgrade this module).
  - Refresh the browser to clear view cache.
  - Confirm Developer mode is enabled and inspect Sales Analysis views.

- **Unexpected customers included/excluded:**

  - Only orders in states ``sale`` and ``done`` are considered for Last Order Date.
  - Quotations (``draft``, ``sent``) and cancelled orders are excluded.

- **Multi-company behavior:**

  - ``sale.report`` already applies standard company access and currency table handling.
  - Results depend on companies visible to the current user.

- **What to check in logs:**

  - Logger: ``odoo.addons.inactive_customer_reporting.models.sale_report``
  - Expected INFO lines during report query build:

    - ``inactive_customer_reporting: building sale.report query``
    - ``inactive_customer_reporting: added 'partner_last_order_date' in sale.report SQL select``

Optional server action snippet (not installed by default)
---------------------------------------------------------

Use this snippet in a manual **Server Action** on model ``res.partner`` to post
an audit message in selected customers' chatter:

.. code-block:: python

    today = fields.Date.context_today(env.user)
    for partner in records:
        partner.message_post(body=f"Inactive customer review run on {today}")

