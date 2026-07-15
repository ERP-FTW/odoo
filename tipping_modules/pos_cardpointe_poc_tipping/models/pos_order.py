from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _payment_fields(self, order, ui_paymentline):
        values = super()._payment_fields(order, ui_paymentline)
        tip_amount = ui_paymentline.get('cardpointe_tip_amount') or 0.0
        values.update({
            'cardpointe_tip_amount': tip_amount,
            'cardpointe_base_amount': ui_paymentline.get('cardpointe_base_amount') or 0.0,
        })
        if 'tip_amount' in self.env['pos.payment']._fields:
            values['tip_amount'] = tip_amount
        return values
