# -*- coding: utf-8 -*-
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # NOTE: stock.picking already has carrier_tracking_ref (standard).
    # We add the same field name to sale.order for UX + easy propagation.
    carrier_tracking_ref = fields.Char(
        string="Delivery Tracking Reference",
        copy=False,
        help="Tracking reference entered on the Sales Order. It will be propagated to Delivery Orders "
             "(carrier_tracking_ref on pickings) and shown on invoices.",
    )

    def _prepare_picking(self):
        """Propagate SO tracking reference to the outgoing picking at creation time."""
        self.ensure_one()
        vals = super()._prepare_picking()
        if self.carrier_tracking_ref:
            vals["carrier_tracking_ref"] = self.carrier_tracking_ref
            _logger.debug(
                "SO %s: setting carrier_tracking_ref on new picking to %s",
                self.name,
                self.carrier_tracking_ref,
            )
        return vals

    def write(self, vals):
        """If the SO tracking ref changes, push it to not-done pickings.

        Avoid overwriting a picking tracking ref that has been manually changed
        (unless it still matches the old SO value).
        """
        if "carrier_tracking_ref" not in vals:
            return super().write(vals)

        old_map = {o.id: o.carrier_tracking_ref for o in self}
        res = super().write(vals)
        new_ref = vals.get("carrier_tracking_ref") or False

        for order in self:
            old_ref = old_map.get(order.id)

            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ("done", "cancel")
                and (not p.carrier_tracking_ref or p.carrier_tracking_ref == old_ref)
            )
            if pickings:
                pickings.write({"carrier_tracking_ref": new_ref})
                _logger.info(
                    "SO %s: propagated carrier_tracking_ref=%s to %s picking(s).",
                    order.name,
                    new_ref,
                    len(pickings),
                )
            else:
                _logger.debug(
                    "SO %s: no eligible pickings to propagate (old=%s new=%s).",
                    order.name,
                    old_ref,
                    new_ref,
                )

        return res
