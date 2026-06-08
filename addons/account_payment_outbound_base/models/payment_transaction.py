import json
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    account_payment_id = fields.Many2one('account.payment', index=True, ondelete='cascade')
    is_outbound_payout = fields.Boolean(default=False, index=True)
    provider_status_code = fields.Char(copy=False, readonly=True)
    provider_status_raw = fields.Text(copy=False, readonly=True)
    provider_request_payload = fields.Text(copy=False, readonly=True)
    provider_response_payload = fields.Text(copy=False, readonly=True)
    provider_funding_date = fields.Date(copy=False, readonly=True)
    ach_return_code = fields.Char(copy=False, readonly=True)

    def _is_outbound_provider_transaction(self):
        self.ensure_one()
        return bool(self.is_outbound_payout and self.account_payment_id)

    def _log_outbound_event(self, direction, payload=None, note=None):
        self.ensure_one()
        serialized = payload if isinstance(payload, str) else json.dumps(payload or {}, default=str)
        self.env['outbound.payment.event.log'].sudo().create({
            'transaction_id': self.id,
            'payment_id': self.account_payment_id.id,
            'direction': direction,
            'note': note,
            'payload': serialized,
        })
        _logger.info('Outbound tx=%s direction=%s note=%s', self.reference, direction, note)

    def _refresh_outbound_provider_status(self):
        for tx in self:
            if not tx._is_outbound_provider_transaction():
                continue
            method_name = '_%s_refresh_status_from_funding' % tx.provider_code
            if hasattr(tx, method_name):
                getattr(tx, method_name)()
            else:
                tx._log_outbound_event('manual', note='No provider-specific refresh handler implemented.')
