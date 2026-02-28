import logging
from decimal import Decimal, ROUND_HALF_UP

import requests

_logger = logging.getLogger(__name__)


def _mask_secret(value):
    if not value:
        return '-'
    text = str(value)
    if len(text) <= 8:
        return '***'
    return f"{text[:4]}...{text[-4:]}"


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

    def _safe_headers(self, headers):
        safe = dict(headers)
        if 'Authorization' in safe:
            safe['Authorization'] = f"masked:{_mask_secret(safe['Authorization'])}"
        if 'X-CardConnect-SessionKey' in safe:
            safe['X-CardConnect-SessionKey'] = f"masked:{_mask_secret(safe['X-CardConnect-SessionKey'])}"
        return safe

    def _request(self, method, path, payload=None, session_key=None, timeout=30):
        url = self._url(path)
        headers = self._headers(session_key=session_key)
        _logger.info(
            "CardPointe request method=%s path=%s headers=%s payload=%s timeout=%s",
            method,
            path,
            self._safe_headers(headers),
            payload or {},
            timeout,
        )
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
        except requests.Timeout:
            _logger.warning("CardPointe timeout method=%s path=%s", method, path)
            return {'ok': False, 'status': 'timeout', 'message': 'Terminal request timed out.'}
        except requests.RequestException as exc:
            _logger.exception("CardPointe request failed method=%s path=%s", method, path)
            return {'ok': False, 'status': 'error', 'message': str(exc)}

        _logger.info(
            "CardPointe response method=%s path=%s status=%s body=%s",
            method,
            path,
            response.status_code,
            (response.text or '')[:500],
        )

        data = {}
        if response.text:
            try:
                data = response.json()
            except ValueError:
                data = {}

        return {'ok': True, 'http_status': response.status_code, 'data': data, 'headers': dict(response.headers), 'text': response.text}

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

    def _to_implied_cents(self, amount_dollars):
        value = Decimal(str(amount_dollars)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return str(int(value * 100))

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
            'amount': self._to_implied_cents(amount_dollars),
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
        data = result.get('data') or {}

        error_code = data.get('errorCode')
        error_message = data.get('errorMessage') or data.get('resptext') or data.get('message')

        if error_code == 9:
            status = 'merchant_mode'
        elif error_code == 8:
            status = 'cancelled'
        elif error_code == 7:
            status = 'in_use'
        elif error_code:
            status = 'error'
        else:
            # authCard success/decline should be driven by respstat and/or respcode.
            # respstat: A=Approved, B=Retry, C=Declined (per spec).
            respstat = (data.get('respstat') or '').strip().upper()
            respcode = str(data.get('respcode') or '').strip()
            resptext = (data.get('resptext') or '').strip()

            # Common approved codes observed: "000" (Gateway-style) and sometimes "00"
            if respstat == 'A' or respcode in ('000', '00') or resptext.lower().startswith('approv'):
                status = 'approved'
            elif respstat == 'C':
                status = 'declined'
            elif respstat == 'B':
                status = 'retry'
            elif http_status and http_status >= 400:
                status = 'error'
            else:
                status = 'error'

        normalized = {
            'ok': status == 'approved',
            'status': status,
            'retref': data.get('retref'),
            'authcode': data.get('authcode'),
            'respcode': data.get('respcode') or str(error_code or ''),
            'resptext': data.get('resptext') or error_message,
            'amount': data.get('amount'),
            'token': data.get('token'),
            # IMPORTANT: don't keep the full raw response (it contains huge signature blobs)
            # Keep only a tiny subset for debugging.
            'raw': {
                'respstat': data.get('respstat'),
                'respcode': data.get('respcode'),
                'resptext': data.get('resptext'),
                'retref': data.get('retref'),
                'authcode': data.get('authcode'),
            },
        }
        if not normalized['ok']:
            normalized['message'] = normalized.get('resptext') or f'authCard failed (HTTP {http_status}).'
        return normalized
