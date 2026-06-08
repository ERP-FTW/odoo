import json
import logging
from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError

from .fiserv_ach_client import FiservACHClient

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _send_payment_request(self):
        self.ensure_one()
        super()._send_payment_request()
        if self.provider_code != 'fiserv_ach_outbound' or not self.is_outbound_payout:
            return
        self._fiserv_send_outbound_ach_request()

    def _fiserv_send_outbound_ach_request(self):
        self.ensure_one()
        if self.state in ('pending', 'done') and self.provider_reference:
            raise UserError(_('Transaction already sent to provider and cannot be duplicated.'))
        payment = self.account_payment_id
        provider = self.provider_id
        self._fiserv_validate_before_send(payment, provider)
        partner_bank = payment.partner_bank_id
        payload = self._fiserv_build_auth_payload(payment, partner_bank, provider)
        client = FiservACHClient(provider)
        self.provider_request_payload = client.dumps_masked(payload)
        self._log_outbound_event('request', payload=client.mask_payload(payload), note='Authorization request')
        response = client.authorize(payload)
        self.provider_response_payload = json.dumps(response, default=str)
        self.provider_status_code = response.get('respcode')
        self.provider_status_raw = response.get('resptext') or response.get('respstat')
        self.provider_reference = response.get('retref') or self.provider_reference
        self._log_outbound_event('response', payload=response, note='Authorization response')
        approved = str(response.get('respcode') or '') in ('00', '000') or str(response.get('respstat') or '').upper() in ('A', 'APPROVED')
        if approved:
            self._set_pending(state_message=_('ACH authorization accepted; awaiting funding confirmation.'))
        else:
            message = response.get('resptext') or _('ACH authorization was declined.')
            self._set_error(_('Fiserv ACH decline: %s') % message)

    def _fiserv_validate_before_send(self, payment, provider):
        if payment.currency_id.name != 'USD':
            raise UserError(_('Fiserv ACH outbound only supports USD payments.'))
        if not payment.partner_bank_id:
            raise UserError(_('Vendor bank account is required on the payment.'))
        bank = payment.partner_bank_id
        if not bank.allow_outbound_ach:
            raise UserError(_('The selected vendor bank account is not allowed for outbound ACH.'))
        if not bank.ach_account_type:
            raise UserError(_('Set ACH account type (Checking/Savings) on vendor bank account.'))
        if not (bank.ach_profile_id or bank.ach_token or bank.acc_number):
            raise UserError(_('Missing ACH destination: set profile, token, or account number.'))
        if bank.acc_number and not (bank.ach_profile_id or bank.ach_token) and not bank.bank_aba:
            raise UserError(_('Routing number (ABA) is required when using clear account number.'))
        creds = provider._fiserv_get_effective_credentials()
        if not provider._fiserv_get_effective_base_url() or not creds.get('merchid'):
            raise UserError(_('Fiserv ACH credentials are incomplete on provider configuration.'))

    def _fiserv_build_auth_payload(self, payment, bank, provider):
        creds = provider._fiserv_get_effective_credentials()
        description = (provider.fiserv_ach_default_description or 'PAYMENT')[:10]
        account = bank.ach_profile_id or bank.ach_token or bank.acc_number
        payload = {
            'merchid': creds['merchid'],
            'amount': '%.2f' % payment.amount,
            'accttype': bank.ach_account_type,
            'account': account,
            'name': bank.ach_account_holder_name or payment.partner_id.name,
            'currency': 'USD',
            'orderid': self.reference,
            'achEntryCode': provider.fiserv_ach_default_entry_code or 'CCD',
            'achDescription': description,
        }
        if provider.fiserv_ach_default_ecomind:
            payload['ecomind'] = provider.fiserv_ach_default_ecomind
        if not (bank.ach_profile_id or bank.ach_token):
            payload['bankaba'] = bank.bank_aba
        return payload

    def _fiserv_ach_outbound_refresh_status_from_funding(self):
        for tx in self:
            tx._fiserv_refresh_status_from_funding()

    def _fiserv_refresh_status_from_funding(self):
        self.ensure_one()
        if not self.provider_reference:
            self._set_pending(state_message=_('No provider reference yet; still waiting.'))
            return
        client = FiservACHClient(self.provider_id)
        merchid = self.provider_id._fiserv_get_effective_credentials().get('merchid')
        base_date = self.account_payment_id.date or fields.Date.today()
        found = None
        for offset in range(0, 6):
            current = base_date + timedelta(days=offset)
            response = client.fetch_funding(merchid, current.strftime('%Y%m%d'))
            rows = response if isinstance(response, list) else response.get('funding', [])
            self._log_outbound_event('poll', payload=response, note='Funding lookup %s' % current)
            for row in rows:
                if str(row.get('retref')) == str(self.provider_reference) and str(row.get('cardbrand', '')).upper() == 'ECHECK':
                    found = row
                    break
            if found:
                break
        self.account_payment_id.outbound_last_sync_at = fields.Datetime.now()
        if not found:
            self._set_pending(state_message=_('ACH funding record not yet available.'))
            return
        self.provider_funding_date = found.get('date')
        if found.get('achreturncode'):
            self.ach_return_code = found.get('achreturncode')
            self._set_error(_('ACH returned by bank with code %s.') % self.ach_return_code)
            return
        status = str(found.get('status') or found.get('respstat') or '').lower()
        if status in ('funded', 'settled', 'complete', 'completed'):
            self._set_done(state_message=_('ACH funding confirmed.'))
        else:
            self._set_pending(state_message=_('ACH still pending funding confirmation.'))

    # TODO: add webhook reconciliation and NACHA-compliant reversal support in a future version.
