import logging

from .http import CardPointeRequestError, redact_payload, request_json, safe_log_headers, safe_truncate
from .money import format_gateway_amount

_logger = logging.getLogger(__name__)


def choose_refund_operation(inquire_data):
    """Return 'void' when inquiry shows an unsettled tx, otherwise 'refund'."""
    data = inquire_data or {}
    settle_status = str(
        data.get('setlstat')
        or data.get('settlestat')
        or data.get('settle_status')
        or data.get('settleStatus')
        or ''
    ).strip().lower()

    if settle_status in {'0', 'n', 'no', 'pending', 'not settled', 'not_settled', 'queued'}:
        return 'void'
    if settle_status in {'1', 'y', 'yes', 'settled', 'complete', 'captured'}:
        return 'refund'

    # Conservative default: refund if status is unknown.
    return 'refund'


class CardPointeGatewayClient:
    def __init__(self, config):
        self.config = config
        self.base_url = (config.gateway_base_url or '').rstrip('/')

    def _url(self, path):
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method, path, payload=None, timeout=30):
        url = self._url(path)
        headers = {'Accept': 'application/json'}
        if payload is not None:
            headers['Content-Type'] = 'application/json'

        _logger.info(
            "CardPointe gateway request method=%s path=%s headers=%s payload=%s",
            method,
            path,
            safe_log_headers(headers),
            redact_payload(payload or {}),
        )

        try:
            status_code, response_headers, text, response_json = request_json(
                method=method,
                url=url,
                headers=headers,
                json=payload,
                timeout=timeout,
                auth=(self.config.gateway_username or '', self.config.gateway_password or ''),
            )
        except CardPointeRequestError as exc:
            message = str(exc)
            _logger.warning("CardPointe gateway request failed method=%s path=%s reason=%s", method, path, message)
            return {
                'ok': False,
                'http_status': None,
                'data': {},
                'message': 'Gateway request timed out.' if 'timeout' in message.lower() else message,
                'error_code': 'timeout' if 'timeout' in message.lower() else 'request_error',
            }

        _logger.info(
            "CardPointe gateway response method=%s path=%s status=%s body=%s",
            method,
            path,
            status_code,
            safe_truncate(text),
        )

        data = response_json or {}
        if status_code >= 400:
            return {
                'ok': False,
                'http_status': status_code,
                'data': data,
                'message': data.get('resptext') or data.get('error') or safe_truncate(text),
                'error_code': data.get('respcode') or 'http_error',
            }

        return {
            'ok': True,
            'http_status': status_code,
            'data': data,
            'headers': response_headers,
        }

    def inquire(self, retref, merchid):
        return self._request('GET', f"inquire/{retref}/{merchid}", timeout=20)

    def void(self, merchid, retref):
        return self._request('POST', 'void', payload={'merchid': merchid, 'retref': retref}, timeout=30)

    def refund(self, merchid, retref, amount):
        return self._request(
            'POST',
            'refund',
            payload={'merchid': merchid, 'retref': retref, 'amount': format_gateway_amount(amount)},
            timeout=30,
        )

    def void_or_refund(self, merchid, retref, amount):
        inquire_result = self.inquire(retref, merchid)
        if not inquire_result.get('ok'):
            return {
                'ok': False,
                'status': 'error',
                'message': inquire_result.get('message') or 'CardPointe inquire failed.',
                'operation': 'inquire',
                'raw': inquire_result,
            }

        operation = choose_refund_operation(inquire_result.get('data'))
        if operation == 'void':
            action_result = self.void(merchid, retref)
        else:
            action_result = self.refund(merchid, retref, amount)

        data = action_result.get('data') or {}
        respstat = (data.get('respstat') or '').upper()
        respcode = str(data.get('respcode') or '')
        ok = action_result.get('ok') and (respstat == 'A' or respcode in {'000', '00'})
        message = data.get('resptext') or ('Approved' if ok else action_result.get('message') or 'CardPointe operation failed.')

        return {
            'ok': ok,
            'status': 'approved' if ok else 'error',
            'operation': operation,
            'retref': data.get('retref') or retref,
            'respstat': data.get('respstat'),
            'respcode': data.get('respcode'),
            'resptext': message,
            'raw': {'inquire': inquire_result.get('data') or {}, operation: data},
        }
