# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models

from odoo.addons.payment import setup_provider

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _register_hook(self):
        """Ensure CardPointe provider setup exists on upgrades."""
        res = super()._register_hook()
        try:
            setup_provider(self.env.cr, self.env.registry, 'cardpointe')
        except Exception:
            _logger.exception('[CARDPOINTE] Failed to setup provider during registry hook.')
        return res

    @api.depends('code')
    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'cardpointe').update({
            'support_manual_capture': False,
            'support_refund': False,
            'support_tokenization': False,
        })
