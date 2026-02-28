import logging

from odoo.addons.cardpointe_api_base.services.http import (
    CardPointeRequestError,
    request_json,
    safe_log_headers,
    safe_truncate,
)
from odoo.addons.cardpointe_api_base.services.money import dollars_to_implied_cents
from odoo.addons.cardpointe_api_base.services.normalize import normalize_terminal_authcard_response

_logger = logging.getLogger(__name__)


class CardPointeTerminalClient:
    def __init__(self, config):
        self.config = config
        self.base_url = (config.base_url or '').rstrip('/')

    def _url(self, path):
        return f"{self.base_url}{path}"

    def _headers(self, session_key=None):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Odoo/18 pos_cardpointe_poc',
            'Authorization': self.config.auth_key,
        }
        if session_key:
            headers['X-CardConnect-SessionKey'] = session_key
        return headers

    def _request(self, method, path, payload=None, session_key=None, timeout=30):
        url = self._url(path)
        headers = self._headers(session_key=session_key)
        _logger.info(
            "CardPointe request method=%s path=%s headers=%s payload=%s timeout=%s",
            method,
            path,
            safe_log_headers(headers),
            payload or {},
            timeout,
        )
        try:
            status_code, response_headers, text, response_json = request_json(
                method,
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except CardPointeRequestError as exc:
            message = str(exc)
            status = 'timeout' if 'timeout' in message.lower() else 'error'
            _logger.warning("CardPointe request failed method=%s path=%s reason=%s", method, path, message)
            return {
                'ok': False,
                'status': status,
                'message': 'Terminal request timed out.' if status == 'timeout' else message,
            }

        _logger.info(
            "CardPointe response method=%s path=%s status=%s body=%s",
            method,
            path,
            status_code,
            safe_truncate(text),
        )

        return {
            'ok': True,
            'http_status': status_code,
            'data': response_json or {},
            'headers': response_headers,
            'text': text,
        }

    def connect(self):
        payload = {
            'merchantId': self.config.merchant_id,
            'hsn': self.config.device_serial,
        }
        result = self._request('POST', '/v2/connect', payload=payload, timeout=15)
        if not result.get('ok'):
            return result

        header_value = result['headers'].get('X-CardConnect-SessionKey', '')
        session_key = header_value.split(';', 1)[0].strip()
        if result['http_status'] != 200 or not session_key:
            return {
                'ok': False,
                'status': 'error',
                'message': f"Connect failed (HTTP {result['http_status']}).",
                'raw': result,
            }

        return {'ok': True, 'session_key': session_key}

    def auth_card(self, amount_dollars, order_id):
        connect_result = self.connect()
        if not connect_result.get('ok'):
            return {
                'ok': False,
                'status': connect_result.get('status', 'error'),
                'message': connect_result.get('message', 'Unable to connect terminal session.'),
            }

        payload = {
            'merchantId': self.config.merchant_id,
            'hsn': self.config.device_serial,
            'amount': dollars_to_implied_cents(amount_dollars),
            'capture': True,
            'orderId': order_id,
        }
        result = self._request(
            'POST',
            '/v4/authCard',
            payload=payload,
            session_key=connect_result['session_key'],
            timeout=max(30, self.config.request_timeout_seconds or 120),
        )
        if not result.get('ok'):
            return result

        http_status = result.get('http_status')
        data = dict(result.get('data') or {})
        if 'signature' in data:
            data.pop('signature')

        normalized = normalize_terminal_authcard_response(http_status, data)
        response_message = normalized.get('resptext') or 'Terminal payment failed.'

        _logger.info(
            "CardPointe authCard mapped status=%s ok=%s respcode=%s retref=%s",
            normalized.get('status'),
            normalized.get('ok'),
            normalized.get('respcode'),
            normalized.get('retref'),
        )

        return {
            'ok': normalized.get('ok'),
            'status': normalized.get('status'),
            'message': response_message,
            'respcode': normalized.get('respcode'),
            'resptext': normalized.get('resptext'),
            'retref': normalized.get('retref'),
            'authcode': normalized.get('authcode'),
            'amount': data.get('amount'),
            'token': normalized.get('token'),
            'entrymode': normalized.get('entrymode'),
            'emvTagData': normalized.get('emvTagData'),
            'raw': data,
        }
