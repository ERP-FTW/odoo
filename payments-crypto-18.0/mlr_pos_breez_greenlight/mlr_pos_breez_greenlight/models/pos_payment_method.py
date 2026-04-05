# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import os
from types import SimpleNamespace

import breez_sdk

from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('breez', 'Breez')]

    breez_payment_type = fields.Selection(
        [('lightning', 'BTC-Lightning')],
        string='Breez Payment Type',
        default='lightning',
    )
    breez_invite_code = fields.Char(string='Breez Invite Code')
    breez_mnemonic = fields.Char(string='Breez Mnemonic')
    breez_working_dir = fields.Char(string='Breez Working Directory')

    def _get_breez_settings(self):
        self.ensure_one()
        working_dir = (self.breez_working_dir or '').strip()
        api_key = (self.api_key or '').strip()
        mnemonic = (self.breez_mnemonic or '').strip()
        invite_code = (self.breez_invite_code or '').strip()

        if not working_dir:
            raise UserError(_('Please set a Breez working directory on this payment method.'))
        if not api_key:
            raise UserError(_('Please set the API Key for Breez on this payment method.'))
        if not mnemonic:
            raise UserError(_('Please set the Breez Mnemonic on this payment method.'))

        return {
            'working_dir': working_dir,
            'api_key': api_key,
            'mnemonic': mnemonic,
            'invite_code': invite_code,
        }

    def _build_breez_config(self):
        settings = self._get_breez_settings()
        os.makedirs(settings['working_dir'], exist_ok=True)
        config = breez_sdk.default_config(
            env_type=breez_sdk.EnvironmentType.PRODUCTION,
            api_key=settings['api_key'],
            node_config=breez_sdk.NodeConfig.GREENLIGHT(
                config=breez_sdk.GreenlightNodeConfig(
                    partner_credentials=None,
                    invite_code=settings['invite_code'],
                )
            ),
        )
        config.working_dir = settings['working_dir']
        return config

    def call_breez_sdk(self):
        self.ensure_one()
        try:
            settings = self._get_breez_settings()
            seed = breez_sdk.mnemonic_to_seed(settings['mnemonic'])
            connect_request = breez_sdk.ConnectRequest(
                config=self._build_breez_config(),
                seed=seed,
                restore_only=True,
            )
            return breez_sdk.connect(req=connect_request, listener=SDKListener())
        except Exception as error:
            _logger.exception('Breez connection failed')
            raise UserError(_('API call failure: %s') % error)

    def _test_connection(self):
        if self.use_payment_terminal != 'breez':
            return super()._test_connection()
        self.call_breez_sdk().node_info()
        return SimpleNamespace(status_code=200)

    def action_get_conversion_rate(self):
        try:
            fiat_rates = self.call_breez_sdk().fetch_fiat_rates()
            usd_rates = [rate for rate in fiat_rates if rate.coin == 'USD']
            return usd_rates[0].value if usd_rates else None
        except Exception as error:
            raise UserError(_('Get Conversion Rate: %s') % error)

    def get_amount_sats(self, pos_payment_obj):
        try:
            breez_conversion_rate = self.action_get_conversion_rate()
            amount_sats = round((float(pos_payment_obj.get('amount')) / float(breez_conversion_rate)) * 100000000, 1)
            return {
                'conversion_rate': breez_conversion_rate,
                'invoiced_sat_amount': amount_sats,
            }
        except Exception as error:
            raise UserError(_('Get Millisat amount: %s') % error)

    def breez_create_crypto_invoice_direct_invoice(self, args):
        try:
            invoiced_info = self.get_amount_sats(args)
            amount_millisats = int(invoiced_info['invoiced_sat_amount']) * 1000
            req = breez_sdk.ReceivePaymentRequest(
                amount_msat=amount_millisats,
                description='Invoice for Odoo',
            )
            create_invoice_object = self.call_breez_sdk().receive_payment(req)
            invoice = create_invoice_object.ln_invoice.bolt11
            return {
                'code': 0,
                'invoice_id': create_invoice_object.ln_invoice.payment_hash,
                'invoice': invoice,
                'cryptopay_payment_link': f'lightning:{invoice}',
                'cryptopay_payment_type': 'BTC-lightning',
                'crypto_amt': float(amount_millisats) / 1000,
            }
        except Exception as error:
            _logger.exception('Breez direct invoice creation failed')
            return {'code': str(error)}

    @api.model
    def breez_create_crypto_invoice(self, args):
        try:
            cryptopay_pm = self.env['pos.payment.method'].browse(args['pm_id'])
            if cryptopay_pm.use_payment_terminal != 'breez':
                return {'code': _('Payment method is not configured for Breez.')}
            return cryptopay_pm.breez_create_crypto_invoice_direct_invoice(args)
        except Exception as error:
            _logger.exception('Breez create invoice failed')
            return {'code': str(error)}

    def breez_check_payment_status_direct_invoice(self, args):
        try:
            cryptopay_pm = self.env['pos.payment.method'].browse(args['pm_id'])
            if cryptopay_pm.use_payment_terminal != 'breez':
                return {'code': _('Payment method is not configured for Breez.')}

            sdk = cryptopay_pm.call_breez_sdk()
            payment = sdk.payment_by_hash(args['invoice_id'])

            if payment is None:
                return {'code': 404, 'status': 'not_found'}

            status_name = getattr(payment.status, 'name', str(payment.status)).lower()
            return {
                'code': 0,
                'status': status_name,
                'payment_hash': payment.id,
                'amount_msat': payment.amount_msat,
                'fee_msat': payment.fee_msat,
                'description': payment.description,
            }
        except Exception as error:
            _logger.exception('Breez status check failed')
            return {'code': str(error)}

    @api.model
    def breez_check_payment_status(self, args):
        return self.breez_check_payment_status_direct_invoice(args)


class SDKListener(breez_sdk.EventListener):
    def on_event(self, event):
        _logger.debug('Breez SDK event received: %s', event)
