# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)

ENDPOINT_CHARGE = "/auth"


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """Expose the canonical payment access token for checkout RPC flows."""
        self.ensure_one()
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'cardpointe':
            return res
        res['access_token'] = payment_utils.generate_access_token(
            processing_values['partner_id'],
            processing_values['amount'],
            processing_values['currency_id'],
        )
        return res

    def _cardpointe_charge_from_token(self, token, meta=None):
        """Charge a transaction using a CardPointe hosted token.

        Docs: Gateway API https://developer.fiserv.com/product/CardPointe/docs/?path=docs/APIs/CardPointeGatewayAPI.md
        Docs: Tokenizer https://developer.fiserv.com/product/CardPointe/docs/?path=docs/documentation/HostediFrameTokenizer.md
        Never log secrets/PAN/CVV; tokens only.
        """
        self.ensure_one()
        if self.provider_code != 'cardpointe':
            return {'ok': False, 'message': _("CardPointe: invalid provider.")}

        if self.state in ('done', 'authorized') or self.provider_reference:
            message = _("CardPointe: transaction already processed.")
            self._cardpointe_fail(message)
            return {'ok': False, 'message': message}

        if not ENDPOINT_CHARGE:
            raise UserError(_(
                "CardPointe: charge endpoint is not configured. See docs/ENDPOINTS.md"
            ))

        token_last4 = token[-4:] if isinstance(token, str) else '****'
        _logger.info(
            "[CARDPOINTE] charge request tx_ref=%s token_last4=%s",
            self.reference, token_last4,
        )

        provider = self.provider_id

        # You MUST have these configured on the provider (fields names may differ in your module)
        mid = getattr(provider, "cardpointe_mid", None) or getattr(provider, "cardpointe_merchid", None)
        if not mid:
            raise UserError(_("CardPointe: missing MID on the payment provider (cardpointe_mid)."))

        payload = {
            "merchid": mid,
            "account": token,  # hosted iFrame token
            "amount": ("%.2f" % (self.amount or 0.0)),
            "currency": self.currency_id.name,  # e.g. USD
            "capture": "y",  # "sale" behavior via auth+capture
            "orderid": self.reference,
        }

        response = self.provider_id.with_context(
            cardpointe_tx_reference=self.reference
        )._cardpointe_request('POST', ENDPOINT_CHARGE, payload=payload)

        if response['ok']:
            self._cardpointe_set_provider_reference(response['data'] or {})
            self._cardpointe_done(_("CardPointe payment approved."))
            return {'ok': True, 'message': _("Payment approved.")}

        message = response.get('error_message') or _("CardPointe payment failed.")
        self._cardpointe_fail(message, response.get('error_code'))
        _logger.info(
            "[CARDPOINTE] charge failure tx_ref=%s correlation_id=%s http_status=%s code=%s",
            self.reference,
            response.get('correlation_id'),
            response.get('http_status'),
            response.get('error_code'),
        )
        return {'ok': False, 'message': message}