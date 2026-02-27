import logging

from odoo import http
from odoo.http import request

from ..services.cardpointe_terminal import CardPointeTerminalClient

_logger = logging.getLogger(__name__)


class PosCardPointeController(http.Controller):

    @http.route('/pos_cardpointe_poc/start', type='json', auth='user')
    def start(self, pos_config_id, payment_method_id, amount, currency, order_uid, payment_line_uuid):
        _logger.info(
            "CardPointe POC start called: user=%s pos_config_id=%s payment_method_id=%s amount=%s currency=%s order_uid=%s payment_line_uuid=%s",
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
            _logger.warning("CardPointe POC start failed: POS config not found (%s)", pos_config_id)
            return {'status': 'error', 'message': 'POS config not found.'}
        if pos_config.company_id not in request.env.user.company_ids:
            _logger.warning(
                "CardPointe POC start denied: user=%s company=%s pos_company=%s",
                request.env.user.id,
                request.env.user.company_id.id,
                pos_config.company_id.id,
            )
            return {'status': 'error', 'message': 'Access denied for this POS config.'}

        payment_method = request.env['pos.payment.method'].browse(int(payment_method_id)).exists()
        if not payment_method or payment_method.use_payment_terminal != 'cardpointe_poc':
            _logger.warning(
                "CardPointe POC start failed: invalid payment method id=%s use_payment_terminal=%s",
                payment_method_id,
                payment_method.use_payment_terminal if payment_method else None,
            )
            return {'status': 'error', 'message': 'Invalid payment method.'}

        config = payment_method.cardpointe_config_id
        if not config:
            _logger.warning("CardPointe POC start failed: missing config on payment method id=%s", payment_method.id)
            return {'status': 'error', 'message': 'CardPointe config missing on payment method.'}

        _logger.info(
            "CardPointe POC start using config id=%s base_url=%s port=%s merchant_id=%s device_type=%s device_serial=%s timeout=%s",
            config.id,
            config.base_url,
            config.port,
            config.merchant_id,
            config.device_type,
            config.device_serial or '-',
            config.timeout_seconds,
        )

        client = CardPointeTerminalClient(config)
        result = client.sale(
            amount=float(amount),
            currency=currency,
            merchid=config.merchant_id,
            device_serial=config.device_serial,
            order_uid=order_uid,
        )
        if not result.get('ok'):
            _logger.warning("CardPointe POC start gateway error: %s", result)
            return {'status': result.get('status', 'error'), 'message': result.get('message')}

        _logger.info("CardPointe POC start success: request_id=%s", result.get('request_id'))
        return {
            'status': 'started',
            'request_id': result.get('request_id'),
            'poll_token': f"{payment_line_uuid}:{result.get('request_id')}",
        }

    @http.route('/pos_cardpointe_poc/poll', type='json', auth='user')
    def poll(self, payment_method_id, request_id):
        _logger.info(
            "CardPointe POC poll called: user=%s payment_method_id=%s request_id=%s",
            request.env.user.id,
            payment_method_id,
            request_id,
        )

        payment_method = request.env['pos.payment.method'].browse(int(payment_method_id)).exists()
        if not payment_method:
            _logger.warning("CardPointe POC poll failed: payment method not found (%s)", payment_method_id)
            return {'status': 'error', 'message': 'Payment method not found.'}

        config = payment_method.cardpointe_config_id
        if not config:
            _logger.warning("CardPointe POC poll failed: missing config on payment method id=%s", payment_method.id)
            return {'status': 'error', 'message': 'CardPointe config missing on payment method.'}

        result = CardPointeTerminalClient(config).status(request_id)
        if not result.get('ok'):
            _logger.warning("CardPointe POC poll gateway error: request_id=%s result=%s", request_id, result)
            return {'status': result.get('status', 'error'), 'message': result.get('message')}

        _logger.info(
            "CardPointe POC poll result: request_id=%s status=%s retref=%s authcode=%s message=%s",
            request_id,
            result.get('status'),
            result.get('retref'),
            result.get('authcode'),
            result.get('message'),
        )
        return {
            'status': result.get('status'),
            'retref': result.get('retref'),
            'authcode': result.get('authcode'),
            'amount': result.get('amount'),
            'brand': result.get('brand'),
            'last4': result.get('last4'),
            'message': result.get('message'),
        }
