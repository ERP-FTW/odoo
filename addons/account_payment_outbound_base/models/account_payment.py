import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    outbound_provider_code = fields.Char(copy=False, index=True)
    outbound_transaction_id = fields.Many2one('payment.transaction', copy=False, readonly=True)
    outbound_provider_state = fields.Selection(
        [('draft', 'Draft'), ('pending', 'Pending'), ('done', 'Done'), ('cancel', 'Canceled'), ('error', 'Error')],
        compute='_compute_outbound_provider_state',
    )
    outbound_last_sync_at = fields.Datetime(copy=False, readonly=True)
    outbound_last_error = fields.Text(copy=False, readonly=True)
    can_send_outbound_payment = fields.Boolean(compute='_compute_can_send_outbound_payment')
    can_refresh_outbound_status = fields.Boolean(compute='_compute_can_refresh_outbound_status')
    is_outbound_provider_payment = fields.Boolean(compute='_compute_is_outbound_provider_payment')

    def _is_outbound_provider_payment(self):
        self.ensure_one()
        return self.state == 'posted' and self.payment_type == 'outbound' and self.partner_type == 'supplier' and self.amount > 0

    def _get_outbound_provider_code(self):
        self.ensure_one()
        provider = self._get_outbound_payment_provider()
        return provider.code if provider else False

    def _get_outbound_payment_provider(self):
        self.ensure_one()
        provider = self.journal_id.outbound_payment_provider_id
        return provider if provider and provider.state != 'disabled' else self.env['payment.provider']

    def _get_or_create_outbound_transaction(self):
        self.ensure_one()
        provider = self._get_outbound_payment_provider()
        if not provider:
            raise UserError(_('No outbound payment provider is configured on journal %s.') % self.journal_id.display_name)

        tx = self.outbound_transaction_id
        if tx and tx.state in ('pending', 'done'):
            return tx

        if not tx:
            vals = {
                'provider_id': provider.id,
                'reference': self.name or self.ref or _('Outbound-%s') % self.id,
                'amount': self.amount,
                'currency_id': self.currency_id.id,
                'partner_id': self.partner_id.commercial_partner_id.id,
                'operation': 'offline',
                'account_payment_id': self.id,
                'is_outbound_payout': True,
            }
            tx = self.env['payment.transaction'].create(vals)
            self.outbound_transaction_id = tx
            _logger.info('Created outbound transaction %s for payment %s', tx.reference, self.id)
        return tx

    def action_send_outbound_payment(self):
        self.ensure_one()
        if not self._is_outbound_provider_payment():
            raise UserError(_('Only posted outbound supplier payments with positive amount can be sent.'))
        try:
            provider = self._get_outbound_payment_provider()
            if not provider:
                raise UserError(_('No outbound provider configured on journal.'))
            tx = self._get_or_create_outbound_transaction()
            if tx.state == 'done':
                raise UserError(_('Payment was already sent and marked done.'))
            self.outbound_provider_code = provider.code
            tx._send_payment_request()
            self.outbound_last_error = False
            return True
        except Exception as exc:
            _logger.exception('Failed outbound send for payment %s', self.id)
            self.outbound_last_error = str(exc)
            if self.outbound_transaction_id:
                self.outbound_transaction_id._log_outbound_event('error', note=str(exc))
            if isinstance(exc, UserError):
                raise
            raise UserError(_('Outbound provider request failed: %s') % exc)

    def action_refresh_outbound_status(self):
        self.ensure_one()
        if not self.outbound_transaction_id:
            raise UserError(_('No outbound transaction linked to this payment.'))
        self.outbound_transaction_id._refresh_outbound_provider_status()
        self.outbound_last_sync_at = fields.Datetime.now()
        return True

    def action_view_outbound_transaction(self):
        self.ensure_one()
        if not self.outbound_transaction_id:
            raise UserError(_('No outbound transaction linked to this payment.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.transaction',
            'res_id': self.outbound_transaction_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _compute_outbound_provider_state(self):
        for payment in self:
            payment.outbound_provider_state = payment.outbound_transaction_id.state or 'draft'

    def _compute_can_send_outbound_payment(self):
        for payment in self:
            payment.can_send_outbound_payment = bool(
                payment._is_outbound_provider_payment()
                and payment._get_outbound_payment_provider()
                and (not payment.outbound_transaction_id or payment.outbound_transaction_id.state not in ('pending', 'done'))
            )

    def _compute_can_refresh_outbound_status(self):
        for payment in self:
            payment.can_refresh_outbound_status = bool(payment.outbound_transaction_id and payment.outbound_transaction_id.state in ('pending', 'error'))

    def _compute_is_outbound_provider_payment(self):
        for payment in self:
            payment.is_outbound_provider_payment = payment._is_outbound_provider_payment()
