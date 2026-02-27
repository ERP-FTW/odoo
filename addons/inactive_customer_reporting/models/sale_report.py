import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleReport(models.Model):
    _inherit = 'sale.report'

    # Date is preferred over Datetime to keep pivot grouping and inactivity filtering
    # straightforward and timezone-neutral for this use case.
    partner_last_order_date = fields.Date(
        string='Last Order Date',
        readonly=True,
        group_operator='max',
    )

    def _select_additional_fields(self):
        additional_fields = super()._select_additional_fields()
        additional_fields['partner_last_order_date'] = """
            MAX(CASE
                WHEN s.state IN ('sale', 'done') THEN DATE(s.date_order)
                ELSE NULL
            END)
        """
        _logger.info(
            "inactive_customer_reporting: added 'partner_last_order_date' in sale.report SQL select"
        )
        return additional_fields

    def _query(self):
        _logger.info("inactive_customer_reporting: building sale.report query")
        return super()._query()
