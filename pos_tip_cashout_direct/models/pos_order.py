from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        result = super()._process_payment_lines(pos_order, order, pos_session, draft)
        order._assign_direct_tip_amounts_from_order_tip()
        return result

    def _assign_direct_tip_amounts_from_order_tip(self):
        for order in self:
            payments = order.payment_ids.filtered(lambda payment: not payment.is_change)
            if not order.tip_amount or not payments or any(payments.mapped('tip_amount')):
                continue
            if len(payments) == 1:
                payments.tip_amount = order.tip_amount
