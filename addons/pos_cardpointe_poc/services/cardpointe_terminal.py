import logging

import requests

_logger = logging.getLogger(__name__)


class CardPointeTerminalClient:
    def __init__(self, config):
        self.config = config
        self.timeout = max(5, config.timeout_seconds or 60)
        self.base_url = (config.base_url or '').rstrip('/')

    def _url(self, path):
        return f"{self.base_url}:{self.config.port}{path}"

    def _request(self, method, path, payload=None):
        url = self._url(path)
        _logger.info("CardPointe HTTP request: method=%s url=%s payload=%s", method, url, payload or {})
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                timeout=(10, self.timeout),
                headers={'Content-Type': 'application/json'},
            )
        except requests.Timeout:
            _logger.warning("CardPointe HTTP timeout: method=%s url=%s", method, url)
            return {'ok': False, 'status': 'timeout', 'message': 'CardPointe terminal request timed out.'}
        except requests.RequestException as exc:
            _logger.exception("CardPointe HTTP request exception: method=%s url=%s error=%s", method, url, exc)
            return {'ok': False, 'status': 'error', 'message': str(exc)}

        _logger.info(
            "CardPointe HTTP response: method=%s url=%s status_code=%s body=%s",
            method,
            url,
            response.status_code,
            response.text[:500],
        )

        if response.status_code >= 400:
            return {'ok': False, 'status': 'error', 'message': f'HTTP {response.status_code}: {response.text[:200]}'}

        try:
            return {'ok': True, 'data': response.json()}
        except ValueError:
            _logger.warning("CardPointe HTTP invalid JSON response: method=%s url=%s", method, url)
            return {'ok': False, 'status': 'error', 'message': 'Invalid JSON response from terminal gateway.'}

    def sale(self, amount, currency, merchid, device_serial=None, order_uid=None):
        payload = {
            'amount': f'{amount:.2f}',
            'currency': currency,
            'merchid': merchid,
            'orderid': order_uid,
            'capture': 'y',
        }
        if device_serial:
            payload['deviceid'] = device_serial

        _logger.info(
            "CardPointe sale start: amount=%s currency=%s merchid=%s order_uid=%s device_serial=%s",
            payload['amount'],
            currency,
            merchid,
            order_uid,
            device_serial or '-',
        )
        result = self._request('POST', '/api/v2/connectedterminal/sale', payload)
        if not result['ok']:
            _logger.warning("CardPointe sale failed: %s", result)
            return result

        data = result['data']
        request_id = data.get('requestid') or data.get('request_id') or data.get('retref')
        _logger.info("CardPointe sale accepted: request_id=%s raw=%s", request_id, data)
        return {
            'ok': True,
            'status': 'started',
            'request_id': request_id,
            'raw': data,
        }

    def status(self, request_id):
        _logger.info("CardPointe status check: request_id=%s", request_id)
        result = self._request('GET', f'/api/v2/connectedterminal/status/{request_id}')
        if not result['ok']:
            _logger.warning("CardPointe status failed: request_id=%s result=%s", request_id, result)
            return result

        data = result['data']
        gateway_status = (data.get('respstat') or data.get('status') or '').lower()
        resp_code = (data.get('respcode') or data.get('resp_code') or '').lower()

        if gateway_status in {'approved', 'complete'} or resp_code == '00':
            normalized_status = 'approved'
        elif gateway_status in {'declined'}:
            normalized_status = 'declined'
        elif gateway_status in {'cancelled', 'canceled'}:
            normalized_status = 'cancelled'
        elif gateway_status in {'timeout'}:
            normalized_status = 'timeout'
        elif gateway_status in {'pending', 'in_progress', 'processing'} or not gateway_status:
            normalized_status = 'pending'
        else:
            normalized_status = 'error'

        normalized = {
            'ok': True,
            'status': normalized_status,
            'retref': data.get('retref'),
            'authcode': data.get('authcode'),
            'amount': float(data.get('amount') or 0.0),
            'brand': data.get('cardtype') or data.get('brand'),
            'last4': data.get('acctlastfour') or data.get('last4'),
            'message': data.get('resptext') or data.get('message'),
            'raw': data,
        }
        _logger.info("CardPointe status normalized: request_id=%s normalized=%s", request_id, normalized)
        return normalized
