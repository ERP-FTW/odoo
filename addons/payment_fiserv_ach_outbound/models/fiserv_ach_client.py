import json
import logging

import requests

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FiservACHClient:
    AUTH_PATH = '/cardconnect/rest/auth'
    FUNDING_PATH = '/cardconnect/rest/funding'
    TIMEOUT = 30

    def __init__(self, provider):
        self.provider = provider
        self.base_url = (provider._fiserv_get_effective_base_url() or '').rstrip('/')
        self.credentials = provider._fiserv_get_effective_credentials()

    def _ensure_config(self):
        if not self.base_url:
            raise UserError('Fiserv ACH base URL is missing.')
        if not self.credentials.get('merchid'):
            raise UserError('Fiserv ACH merchant id is missing.')

    def _headers(self):
        headers = {'Content-Type': 'application/json'}
        token = self.credentials.get('auth_token')
        if token:
            headers['Authorization'] = token
        return headers

    def _auth(self):
        username = self.credentials.get('username')
        password = self.credentials.get('password')
        if username and password:
            return (username, password)
        return None

    def _post(self, path, payload):
        self._ensure_config()
        url = f'{self.base_url}{path}'
        _logger.info('Fiserv ACH POST %s', url)
        resp = requests.post(url, headers=self._headers(), auth=self._auth(), json=payload, timeout=self.TIMEOUT)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    @staticmethod
    def mask_payload(payload):
        data = dict(payload or {})
        for key in ('account', 'bankaba'):
            if data.get(key):
                value = str(data[key])
                data[key] = '*' * max(0, len(value) - 4) + value[-4:]
        return data

    def authorize(self, payload):
        return self._post(self.AUTH_PATH, payload)

    def fetch_funding(self, merchid, date_str):
        return self._post(self.FUNDING_PATH, {'merchid': merchid, 'date': date_str})

    @staticmethod
    def dumps_masked(payload):
        return json.dumps(FiservACHClient.mask_payload(payload), default=str)
