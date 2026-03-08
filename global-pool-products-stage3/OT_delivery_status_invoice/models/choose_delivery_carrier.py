# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = "choose.delivery.carrier"

    # keep it editable (simple Char), but prefill from the SO
    carrier_tracking_ref = fields.Char(string="Delivery Tracking Reference")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # order_id is usually provided via context default_order_id
        order_id = res.get("order_id") or self.env.context.get("default_order_id")
        if order_id and "carrier_tracking_ref" in fields_list:
            order = self.env["sale.order"].browse(order_id)
            res["carrier_tracking_ref"] = order.carrier_tracking_ref
            _logger.info(
                "[choose.delivery.carrier] default_get: order=%s(%s) prefilling carrier_tracking_ref=%s",
                order.name, order.id, order.carrier_tracking_ref,
            )
        return res

    @api.onchange("order_id")
    def _onchange_order_id_carrier_tracking_ref(self):
        """If the wizard is opened / changed for a given order, prefill from that order."""
        for wiz in self:
            if wiz.order_id:
                wiz.carrier_tracking_ref = wiz.order_id.carrier_tracking_ref
                _logger.info(
                    "[choose.delivery.carrier] onchange order_id: order=%s(%s) carrier_tracking_ref=%s",
                    wiz.order_id.name, wiz.order_id.id, wiz.carrier_tracking_ref,
                )

    def button_confirm(self):
        """When user clicks Add/Update, write the tracking ref back to the sale order."""
        self.ensure_one()
        res = super().button_confirm()

        if self.order_id:
            # write to SO (this triggers your sale.order.write propagation to pickings)
            self.order_id.write({"carrier_tracking_ref": self.carrier_tracking_ref or False})
            _logger.info(
                "[choose.delivery.carrier] button_confirm: wrote SO=%s(%s) carrier_tracking_ref=%s",
                self.order_id.name, self.order_id.id, self.carrier_tracking_ref,
            )
        else:
            _logger.info("[choose.delivery.carrier] button_confirm: no order_id in wizard; nothing to write")

        return res
