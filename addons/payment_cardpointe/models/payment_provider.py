# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    @api.depends('code')
    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'cardpointe').update({
            'support_manual_capture': False,
            'support_refund': False,
            'support_tokenization': False,
        })
