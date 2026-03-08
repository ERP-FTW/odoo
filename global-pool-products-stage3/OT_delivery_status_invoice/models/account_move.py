# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    delivery_tracking_ref = fields.Char(
        string="Delivery Tracking Reference",
        compute="_compute_delivery_tracking_ref",
        store=True,
        help="Aggregated tracking references from related Sales Orders / Delivery Orders.",
    )

    @api.depends(
        "invoice_origin",
        "invoice_line_ids.sale_line_ids.order_id.carrier_tracking_ref",
        "invoice_line_ids.sale_line_ids.order_id.picking_ids.carrier_tracking_ref",
        "invoice_line_ids.sale_line_ids.order_id.picking_ids.state",
    )
    def _compute_delivery_tracking_ref(self):
        """Compute tracking references for the invoice.

        Priority:
        1) Related pickings' carrier_tracking_ref
        2) Sale Order's carrier_tracking_ref (fallback when pickings don't have it yet)
        3) invoice_origin lookup (fallback) -> then (1) and (2)
        """
        SaleOrder = self.env["sale.order"]

        for move in self:
            refs = set()
            sale_orders = self.env["sale.order"]

            # 1) Related SOs from invoice lines
            for line in move.invoice_line_ids:
                sale_lines = getattr(line, "sale_line_ids", False)
                if sale_lines:
                    sale_orders |= sale_lines.mapped("order_id")

            # 2) Fallback: invoice_origin
            if not sale_orders and move.invoice_origin:
                names = [n.strip() for n in move.invoice_origin.split(",") if n.strip()]
                if names:
                    sale_orders = SaleOrder.search([("name", "in", names)])

            if sale_orders:
                pickings = sale_orders.mapped("picking_ids")
                picking_refs = set(filter(None, pickings.mapped("carrier_tracking_ref")))
                if picking_refs:
                    refs |= picking_refs

                so_refs = set(filter(None, sale_orders.mapped("carrier_tracking_ref")))
                if so_refs:
                    refs |= so_refs

                _logger.debug(
                    "Invoice %s (%s): sale_orders=%s pickings=%s refs=%s",
                    move.name or move.id,
                    move.move_type,
                    ",".join(sale_orders.mapped("name")) if sale_orders else "-",
                    len(pickings),
                    ",".join(sorted(refs)) if refs else "-",
                )

            move.delivery_tracking_ref = ", ".join(sorted(refs))
