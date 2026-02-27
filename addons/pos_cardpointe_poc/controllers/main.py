import logging

from odoo import http
from odoo.http import request

from ..services.cardpointe_terminal import CardPointeTerminalClient

_logger = logging.getLogger(__name__)


class PosCardPointeController(http.Controller):

    @http.route('/pos_cardpointe_poc/start', type='json', auth='user')
    def start(self, pos_config_id, payment_method_id, amount, currency, order_uid, payment_line_uuid):
        _logger.info(
            "CardPointe start user=%s pos_config_id=%s payment_method_id=%s amount=%s currency=%s order_uid=%s line=%s",
            request.env.user.id,
            pos_config_id,
            payment_method_id,
            amount,
            currency,
            order_uid,
            payment_line_uuid,
        )

        pos_config = request.env['pos.config'].browse(int(pos_config_id)).exists()
        if not pos_config:
            return {'status': 'error', 'message': 'POS config not found.'}
        if pos_config.company_id not in request.env.user.company_ids:
            return {'status': 'error', 'message': 'Access denied for this POS config.'}

        payment_method = request.env['pos.payment.method'].browse(int(payment_method_id)).exists()
        if not payment_method or payment_method.use_payment_terminal != 'cardpointe_poc':
            return {'status': 'error', 'message': 'Invalid payment method.'}

        config = payment_method.cardpointe_config_id
        if not config:
            return {'status': 'error', 'message': 'CardPointe config missing on payment method.'}

        result = CardPointeTerminalClient(config).auth_card(amount_dollars=amount, order_id=order_uid)
        if result.get('status') == 'approved':
            return {
                'status': 'approved',
                'retref': result.get('retref'),
                'authcode': result.get('authcode'),
                'respcode': result.get('respcode'),
                'resptext': result.get('resptext'),
                'amount': result.get('amount'),
                'token': result.get('token'),
            }

        return {
            'status': result.get('status', 'error'),
            'message': result.get('message') or result.get('resptext') or 'Terminal payment failed.',
            'respcode': result.get('respcode'),
            'resptext': result.get('resptext'),
        }

    @http.route('/pos_cardpointe_poc/poll', type='json', auth='user')
    def poll(self, payment_method_id, request_id):
        return {
            'status': 'error',
            'message': 'Not implemented for authCard flow.',
        }
