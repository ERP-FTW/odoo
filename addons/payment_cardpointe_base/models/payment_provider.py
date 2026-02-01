# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import cardpointe_client

_logger = logging.getLogger(__name__)

ENDPOINT_TEST_CONNECTION = None  # TODO: set ENDPOINT_TEST_CONNECTION per Gateway API docs.


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('cardpointe', 'CardPointe')], ondelete={'cardpointe': 'set default'})

    cardpointe_api_base = fields.Char(
        string="API Base URL",
        required_if_provider='cardpointe',
        help="Base URL like https://.../cardconnect/rest/",
    )
    cardpointe_username = fields.Char(string="API Username", required_if_provider='cardpointe')
    cardpointe_password = fields.Char(
        string="API Password",
        required_if_provider='cardpointe',
        password=True,
        groups='base.group_system',
    )
    cardpointe_mid = fields.Char(string="Merchant ID (MID)", required_if_provider='cardpointe')
    cardpointe_tokenizer_url = fields.Char(
        string="Hosted iFrame Tokenizer URL",
        required_if_provider='cardpointe',
    )
    cardpointe_test_endpoint = fields.Char(
        string="Test Connection Endpoint",
        help="Relative endpoint for the test connection action (appended to the API base URL).",
    )
    cardpointe_debug_logging = fields.Boolean(string="Enable CardPointe Debug Logging")
    cardpointe_timeout_connect = fields.Integer(string="Connect Timeout (s)", default=10)
    cardpointe_timeout_read = fields.Integer(string="Read Timeout (s)", default=30)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('cardpointe_api_base'):
                vals['cardpointe_api_base'] = self._cardpointe_normalize_base_url(
                    vals['cardpointe_api_base']
                )
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('cardpointe_api_base'):
            vals['cardpointe_api_base'] = self._cardpointe_normalize_base_url(
                vals['cardpointe_api_base']
            )
        return super().write(vals)

    @api.onchange('cardpointe_api_base')
    def _onchange_cardpointe_api_base(self):
        if self.cardpointe_api_base:
            self.cardpointe_api_base = self._cardpointe_normalize_base_url(
                self.cardpointe_api_base
            )

    def _cardpointe_normalize_base_url(self, base_url):
        base_url = (base_url or '').strip()
        if base_url and not base_url.endswith('/'):
            base_url = f"{base_url}/"
        return base_url

    def _cardpointe_request(self, method, endpoint, payload=None, headers=None, timeout=None):
        self.ensure_one()
        return cardpointe_client._cardpointe_request(
            self, method, endpoint, payload=payload, headers=headers, timeout=timeout
        )

    def action_cardpointe_test_connection(self):
        self.ensure_one()
        if self.code != 'cardpointe':
            return
        endpoint = self.cardpointe_test_endpoint or ENDPOINT_TEST_CONNECTION
        if not endpoint:
            raise UserError(_(
                "CardPointe: no test endpoint configured. "
                "Please set the Test Connection Endpoint or ENDPOINT_TEST_CONNECTION "
                "according to docs/ENDPOINTS.md"
            ))

        response = self._cardpointe_request('GET', endpoint)
        if response['ok']:
            message = _(
                "CardPointe connection OK. Base URL: %(base)s MID: %(mid)s",
                base=self.cardpointe_api_base,
                mid=self.cardpointe_mid or '-',
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("CardPointe Connection"),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }

        error_message = (response.get('error_message') or '')[:200]
        message = _(
            "CardPointe connection failed. HTTP: %(status)s Code: %(code)s Message: %(message)s",
            status=response.get('http_status') or '-',
            code=response.get('error_code') or '-',
            message=error_message,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("CardPointe Connection"),
                'message': message,
                'type': 'danger',
                'sticky': False,
            }
        }
