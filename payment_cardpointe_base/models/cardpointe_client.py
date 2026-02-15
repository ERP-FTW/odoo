# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid
from json import JSONDecodeError

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    'authorization',
    'password',
    'token',
    'card',
    'pan',
    'cvv',
    'cvc',
    'number',
    'account',
    'signature',
    'key',
}


# Docs: Gateway API https://developer.fiserv.com/product/CardPointe/docs/?path=docs/APIs/CardPointeGatewayAPI.md
# Docs: Tokenizer https://developer.fiserv.com/product/CardPointe/docs/?path=docs/documentation/HostediFrameTokenizer.md
# Never log secrets/PAN/CVV; redact tokens.

def _mask_token(value):
    if not value:
        return '****'
    if not isinstance(value, str):
        return '****'
    return f"****{value[-4:]}" if len(value) >= 4 else '****'


def _cardpointe_redact(obj):
    """Redact sensitive keys in nested dict/list structures."""
    if isinstance(obj, dict):
        redacted = {}
        for key, value in obj.items():
            key_lower = str(key).lower()
            if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
                if 'token' in key_lower:
                    redacted[key] = _mask_token(value)
                else:
                    redacted[key] = '***'
            else:
                redacted[key] = _cardpointe_redact(value)
        return redacted
    if isinstance(obj, list):
        return [_cardpointe_redact(item) for item in obj]
    return obj


def _cardpointe_request(provider, method, endpoint, payload=None, headers=None, timeout=None):
    """Perform a CardPointe API request and return a normalized response dict."""
    if not provider.cardpointe_api_base:
        raise UserError(_("CardPointe: missing API base URL."))

    correlation_id = uuid.uuid4().hex
    tx_reference = provider.env.context.get('cardpointe_tx_reference')
    operation = f"{method} {endpoint}"

    _logger.info(
        "[CARDPOINTE] operation=%s tx_ref=%s correlation_id=%s",
        operation, tx_reference or '-', correlation_id,
    )

    request_headers = headers.copy() if headers else {}
    if 'Accept' not in request_headers:
        request_headers['Accept'] = 'application/json'
    if payload is not None and 'Content-Type' not in request_headers:
        request_headers['Content-Type'] = 'application/json'

    api_base = provider.cardpointe_api_base
    url = f"{api_base}{endpoint.lstrip('/')}"

    if provider.cardpointe_debug_logging:
        _logger.info(
            "[CARDPOINTE] request method=%s endpoint=%s correlation_id=%s payload=%s",
            method, endpoint, correlation_id, _cardpointe_redact(payload or {}),
        )

    connect_timeout = provider.cardpointe_timeout_connect
    read_timeout = provider.cardpointe_timeout_read
    request_timeout = timeout or (connect_timeout, read_timeout)

    try:
        response = requests.request(
            method=method,
            url=url,
            json=payload,
            headers=request_headers,
            auth=(provider.cardpointe_username or '', provider.cardpointe_password or ''),
            timeout=request_timeout,
        )
        http_status = response.status_code
        try:
            response_data = response.json() if response.content else {}
        except JSONDecodeError:
            response_data = {}
            return {
                'ok': False,
                'data': {},
                'error_message': _("CardPointe returned a non-JSON response."),
                'error_code': None,
                'http_status': http_status,
                'correlation_id': correlation_id,
            }

        if provider.cardpointe_debug_logging:
            _logger.info(
                "[CARDPOINTE] response correlation_id=%s http_status=%s body=%s",
                correlation_id, http_status, _cardpointe_redact(response_data),
            )

        if http_status >= 400:
            error_message = response_data.get('message') or response_data.get('error')
            return {
                'ok': False,
                'data': response_data,
                'error_message': error_message or _("CardPointe request failed."),
                'error_code': response_data.get('code'),
                'http_status': http_status,
                'correlation_id': correlation_id,
            }

        return {
            'ok': True,
            'data': response_data,
            'error_message': '',
            'error_code': None,
            'http_status': http_status,
            'correlation_id': correlation_id,
        }
    except requests.exceptions.Timeout:
        return {
            'ok': False,
            'data': {},
            'error_message': _("CardPointe request timed out."),
            'error_code': 'timeout',
            'http_status': None,
            'correlation_id': correlation_id,
        }
    except requests.exceptions.ConnectionError:
        return {
            'ok': False,
            'data': {},
            'error_message': _("CardPointe connection error."),
            'error_code': 'connection_error',
            'http_status': None,
            'correlation_id': correlation_id,
        }
    except requests.exceptions.RequestException as exc:
        return {
            'ok': False,
            'data': {},
            'error_message': str(exc),
            'error_code': 'request_error',
            'http_status': None,
            'correlation_id': correlation_id,
        }
