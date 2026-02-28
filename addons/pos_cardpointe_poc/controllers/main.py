import logging
import threading
import uuid

from odoo import http
from odoo.http import request

from ..services.cardpointe_terminal import CardPointeTerminalClient

_logger = logging.getLogger(__name__)


class PosCardPointeController(http.Controller):
    _active_requests = {}
    _active_requests_lock = threading.Lock()

    @classmethod
    def _set_active_request(cls, request_id, values):
        with cls._active_requests_lock:
            cls._active_requests[request_id] = values

    @classmethod
    def _get_active_request(cls, request_id):
        with cls._active_requests_lock:
            return cls._active_requests.get(request_id)

    @classmethod
    def _pop_active_request(cls, request_id):
        with cls._active_requests_lock:
            return cls._active_requests.pop(request_id, None)

    def _validate_start_payload(self, pos_config_id, payment_method_id):
        pos_config = request.env['pos.config'].browse(int(pos_config_id)).exists()
        if not pos_config:
            return None, None, {'status': 'error', 'message': 'POS config not found.'}
        if pos_config.company_id not in request.env.user.company_ids:
            return None, None, {'status': 'error', 'message': 'Access denied for this POS config.'}

        payment_method = request.env['pos.payment.method'].browse(int(payment_method_id)).exists()
        if not payment_method or payment_method.use_payment_terminal != 'cardpointe_poc':
            return None, None, {'status': 'error', 'message': 'Invalid payment method.'}

        config = payment_method.cardpointe_config_id
        if not config:
            return None, None, {'status': 'error', 'message': 'CardPointe config missing on payment method.'}

        return payment_method, config, None

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

        _payment_method, config, error = self._validate_start_payload(pos_config_id, payment_method_id)
        if error:
            return error

        connect_result = CardPointeTerminalClient(config).connect()
        if not connect_result.get('ok'):
            _logger.warning(
                "CardPointe start failed to connect user=%s payment_method_id=%s reason=%s",
                request.env.user.id,
                payment_method_id,
                connect_result.get('message'),
            )
            return {
                'status': connect_result.get('status', 'error'),
                'message': connect_result.get('message') or 'Unable to connect terminal session.',
            }

        request_id = str(uuid.uuid4())
        self._set_active_request(
            request_id,
            {
                'session_key': connect_result['session_key'],
                'config_id': config.id,
                'payment_method_id': int(payment_method_id),
                'uid': request.env.uid,
                'order_uid': order_uid,
                'payment_line_uuid': payment_line_uuid,
                'amount': amount,
            },
        )
        _logger.info(
            "CardPointe terminal session established request_id=%s payment_method_id=%s order_uid=%s",
            request_id,
            payment_method_id,
            order_uid,
        )
        return {'status': 'ready', 'request_id': request_id}

    @http.route('/pos_cardpointe_poc/auth', type='json', auth='user')
    def auth(self, request_id):
        active_request = self._get_active_request(request_id)
        if not active_request:
            _logger.warning("CardPointe auth with unknown request_id=%s user=%s", request_id, request.env.user.id)
            return {
                'status': 'error',
                'message': 'Card terminal session expired. Start payment again.',
            }

        if active_request['uid'] != request.env.uid:
            _logger.warning(
                "CardPointe auth access denied request_id=%s expected_uid=%s got_uid=%s",
                request_id,
                active_request['uid'],
                request.env.uid,
            )
            return {'status': 'error', 'message': 'Access denied for this payment session.'}

        payment_method = request.env['pos.payment.method'].browse(active_request['payment_method_id']).exists()
        if not payment_method:
            self._pop_active_request(request_id)
            return {'status': 'error', 'message': 'Payment method no longer available.'}
        config = payment_method.cardpointe_config_id
        if not config:
            self._pop_active_request(request_id)
            return {'status': 'error', 'message': 'CardPointe config missing on payment method.'}

        _logger.info("CardPointe auth started request_id=%s", request_id)
        try:
            result = CardPointeTerminalClient(config).auth_card_with_session(
                amount_dollars=active_request['amount'],
                order_id=active_request['order_uid'],
                session_key=active_request['session_key'],
            )
        finally:
            self._pop_active_request(request_id)

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

    @http.route('/pos_cardpointe_poc/cancel', type='json', auth='user')
    def cancel(self, request_id):
        active_request = self._pop_active_request(request_id)
        if not active_request:
            _logger.warning("CardPointe cancel with unknown request_id=%s user=%s", request_id, request.env.user.id)
            return {
                'status': 'error',
                'message': 'No active CardPointe terminal request found to cancel.',
            }
        if active_request['uid'] != request.env.uid:
            _logger.warning(
                "CardPointe cancel access denied request_id=%s expected_uid=%s got_uid=%s",
                request_id,
                active_request['uid'],
                request.env.uid,
            )
            return {'status': 'error', 'message': 'Access denied for this payment session.'}

        payment_method = request.env['pos.payment.method'].browse(active_request['payment_method_id']).exists()
        if not payment_method or not payment_method.cardpointe_config_id:
            return {'status': 'error', 'message': 'CardPointe config no longer available for cancellation.'}

        result = CardPointeTerminalClient(payment_method.cardpointe_config_id).cancel(active_request['session_key'])
        if result.get('ok'):
            return {
                'status': 'cancelled',
                'message': result.get('message') or 'Cancel accepted by terminal.',
                'respcode': result.get('respcode'),
                'resptext': result.get('resptext'),
            }

        _logger.warning(
            "CardPointe cancel failed request_id=%s message=%s respcode=%s resptext=%s",
            request_id,
            result.get('message'),
            result.get('respcode'),
            result.get('resptext'),
        )
        return {
            'status': 'error',
            'message': result.get('message') or 'Cancel failed.',
            'respcode': result.get('respcode'),
            'resptext': result.get('resptext'),
        }

    @http.route('/pos_cardpointe_poc/poll', type='json', auth='user')
    def poll(self, payment_method_id, request_id):
        return {
            'status': 'error',
            'message': 'Not implemented for authCard flow.',
        }
