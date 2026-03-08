# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Odoo 18 often creates deliveries via procurement/stock rules, not via
        sale.order._prepare_picking(). So we propagate the SO tracking reference
        here, at stock.picking creation time.

        Rules:
        - If caller already set carrier_tracking_ref in vals, do not override.
        - Prefer sale_id if present (fast, reliable).
        - Fallback to origin -> match sale.order.name.
        - Only fill when SO has carrier_tracking_ref.
        """
        SaleOrder = self.env["sale.order"].sudo()

        for vals in vals_list:
            # Respect explicit value
            if vals.get("carrier_tracking_ref"):
                continue

            so = False

            # 1) Prefer sale_id from vals
            sale_id = vals.get("sale_id")
            if sale_id:
                so = SaleOrder.browse(sale_id)

            # 2) Fallback: origin -> try match sale.order.name
            if not so and vals.get("origin"):
                # origin is often "S00012" or can include multiple refs.
                # Keep it simple: first token split by comma.
                origin = vals.get("origin") or ""
                token = origin.split(",")[0].strip()
                if token:
                    so = SaleOrder.search([("name", "=", token)], limit=1)

            if so and so.carrier_tracking_ref:
                vals["carrier_tracking_ref"] = so.carrier_tracking_ref
                _logger.info(
                    "Picking create prefill: set carrier_tracking_ref=%s from SO=%s (origin=%s sale_id=%s)",
                    so.carrier_tracking_ref, so.name, vals.get("origin"), vals.get("sale_id"),
                )

        pickings = super().create(vals_list)

        # Post-create safety net: sometimes sale_id/origin is set after create
        # in certain flows; if carrier_tracking_ref still empty, try to fill.
        to_fill = pickings.filtered(lambda p: not p.carrier_tracking_ref)
        if to_fill:
            # Try using sale_id relation first
            for p in to_fill:
                so = p.sale_id
                if not so and p.origin:
                    token = (p.origin.split(",")[0] or "").strip()
                    if token:
                        so = SaleOrder.search([("name", "=", token)], limit=1)
                if so and so.carrier_tracking_ref:
                    p.carrier_tracking_ref = so.carrier_tracking_ref
                    _logger.info(
                        "Picking post-create fill: picking=%s set carrier_tracking_ref=%s from SO=%s (origin=%s)",
                        p.name, so.carrier_tracking_ref, so.name, p.origin,
                    )

        return pickings
