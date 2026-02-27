import requests


class CardPointeTerminalClient:
    def __init__(self, config):
        self.config = config
        self.timeout = max(5, config.timeout_seconds or 60)
        self.base_url = (config.base_url or '').rstrip('/')

    def _url(self, path):
        return f"{self.base_url}:{self.config.port}{path}"

    def _request(self, method, path, payload=None):
        try:
            response = requests.request(
                method,
                self._url(path),
                json=payload,
                timeout=(10, self.timeout),
                headers={'Content-Type': 'application/json'},
            )
        except requests.Timeout:
            return {'ok': False, 'status': 'timeout', 'message': 'CardPointe terminal request timed out.'}
        except requests.RequestException as exc:
            return {'ok': False, 'status': 'error', 'message': str(exc)}

        if response.status_code >= 400:
            return {'ok': False, 'status': 'error', 'message': f'HTTP {response.status_code}: {response.text[:200]}'}

        try:
            return {'ok': True, 'data': response.json()}
        except ValueError:
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
        result = self._request('POST', '/api/v2/connectedterminal/sale', payload)
        if not result['ok']:
            return result

        data = result['data']
        request_id = data.get('requestid') or data.get('request_id') or data.get('retref')
        return {
            'ok': True,
            'status': 'started',
            'request_id': request_id,
            'raw': data,
        }

    def status(self, request_id):
        result = self._request('GET', f'/api/v2/connectedterminal/status/{request_id}')
        if not result['ok']:
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

        return {
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
