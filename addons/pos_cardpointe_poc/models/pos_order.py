from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _payment_fields(self, order, ui_paymentline):
        values = super()._payment_fields(order, ui_paymentline)
        values.update({
            'cardpointe_retref': ui_paymentline.get('cardpointe_retref'),
            'cardpointe_authcode': ui_paymentline.get('cardpointe_authcode'),
            'cardpointe_status': ui_paymentline.get('cardpointe_status'),
        })
        return values
