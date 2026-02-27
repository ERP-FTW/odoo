from odoo import http
from odoo.http import request

from ..services.cardpointe_terminal import CardPointeTerminalClient


class PosCardPointeController(http.Controller):

    @http.route('/pos_cardpointe_poc/start', type='json', auth='user')
    def start(self, pos_config_id, payment_method_id, amount, currency, order_uid, payment_line_uuid):
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

        client = CardPointeTerminalClient(config)
        result = client.sale(
            amount=float(amount),
            currency=currency,
            merchid=config.merchant_id,
            device_serial=config.device_serial,
            order_uid=order_uid,
        )
        if not result.get('ok'):
            return {'status': result.get('status', 'error'), 'message': result.get('message')}

        return {
            'status': 'started',
            'request_id': result.get('request_id'),
            'poll_token': f"{payment_line_uuid}:{result.get('request_id')}",
        }

    @http.route('/pos_cardpointe_poc/poll', type='json', auth='user')
    def poll(self, payment_method_id, request_id):
        payment_method = request.env['pos.payment.method'].browse(int(payment_method_id)).exists()
        if not payment_method:
            return {'status': 'error', 'message': 'Payment method not found.'}

        config = payment_method.cardpointe_config_id
        if not config:
            return {'status': 'error', 'message': 'CardPointe config missing on payment method.'}

        result = CardPointeTerminalClient(config).status(request_id)
        if not result.get('ok'):
            return {'status': result.get('status', 'error'), 'message': result.get('message')}

        return {
            'status': result.get('status'),
            'retref': result.get('retref'),
            'authcode': result.get('authcode'),
            'amount': result.get('amount'),
            'brand': result.get('brand'),
            'last4': result.get('last4'),
            'message': result.get('message'),
        }
