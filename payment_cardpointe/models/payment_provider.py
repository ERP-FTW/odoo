# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, models

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

    @api.model
    def _setup_provider(self, code):
        """Ensure CardPointe payment method/lines exist so journal can be persisted."""
        res = super()._setup_provider(code)
        if code != 'cardpointe':
            return res

        payment_method = self.env['account.payment.method'].search([('code', '=', code)], limit=1)
        if not payment_method:
            payment_method = self.env['account.payment.method'].sudo().create({
                'name': _('Cardpointe'),
                'code': code,
                'payment_type': 'inbound',
            })

        providers = self.search([('code', '=', code)])
        for provider in providers:
            if provider.journal_id:
                provider._ensure_payment_method_line(allow_create=True)
            else:
                provider._ensure_payment_method_line(allow_create=False)
        return res

    @api.depends('code')
    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'cardpointe').update({
            'support_manual_capture': False,
            'support_refund': False,
            'support_tokenization': False,
        })
