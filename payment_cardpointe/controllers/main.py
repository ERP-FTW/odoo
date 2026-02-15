# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class CardPointeController(http.Controller):

    @http.route('/payment/cardpointe/process', type='json', auth='public')
    def cardpointe_process(self, **kwargs):
        """Process a CardPointe token payment.

        :param str reference: The reference of the transaction
        :param str access_token: The access token used to verify the provided values
        :param str token: The hosted token returned by CardPointe
        :param int partner_id: The partner making the transaction
        :param dict meta: Optional non-sensitive metadata
        :return: A dict with a redirect URL
        """
        reference = kwargs.get('reference')
        access_token = kwargs.get('access_token')
        token = kwargs.get('token')
        partner_id = kwargs.get('partner_id')
        meta = kwargs.get('meta')
        _logger.info(
            "[CARDPOINTE] process request received tx_ref=%s partner_id=%s token_present=%s",
            reference,
            partner_id,
            bool(token),
        )

        missing_fields = []
        if not reference:
            missing_fields.append('reference')
        if not access_token:
            missing_fields.append('access_token')
        if not token:
            missing_fields.append('token')
        if partner_id is None:
            missing_fields.append('partner_id')
        if missing_fields:
            _logger.warning(
                "[CARDPOINTE] Missing required payment data: %s",
                ", ".join(missing_fields),
            )
            raise ValidationError("CardPointe: " + _("Missing required payment data."))
        if not payment_utils.check_access_token(access_token, reference, partner_id):
            raise ValidationError("CardPointe: " + _("Received tampered payment request data."))

        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('reference', '=', reference)
        ], limit=1)
        if not tx_sudo:
            raise ValidationError("CardPointe: " + _("Transaction not found."))

        result = tx_sudo._cardpointe_charge_from_token(token, meta=meta)
        if not result.get('ok'):
            _logger.warning(
                "[CARDPOINTE] process failure tx_ref=%s message=%s",
                reference,
                result.get('message'),
            )
        _logger.info(
            "[CARDPOINTE] process result tx_ref=%s success=%s",
            reference, result.get('ok'),
        )
        return {
            'success': bool(result.get('ok')),
            'redirect_url': '/payment/status',
        }
