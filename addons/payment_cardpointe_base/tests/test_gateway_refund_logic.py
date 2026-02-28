import importlib.util
import os
import sys
import types
import unittest

CURRENT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
SERVICES_DIR = os.path.join(BASE_DIR, 'services')


def _load_services_module(module_name, filename):
    full_name = f'payment_cardpointe_base.services.{module_name}'
    path = os.path.join(SERVICES_DIR, filename)
    spec = importlib.util.spec_from_file_location(full_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


if 'payment_cardpointe_base' not in sys.modules:
    pkg = types.ModuleType('payment_cardpointe_base')
    pkg.__path__ = [BASE_DIR]
    sys.modules['payment_cardpointe_base'] = pkg
if 'payment_cardpointe_base.services' not in sys.modules:
    pkg = types.ModuleType('payment_cardpointe_base.services')
    pkg.__path__ = [SERVICES_DIR]
    sys.modules['payment_cardpointe_base.services'] = pkg

_load_services_module('http', 'http.py')
_load_services_module('money', 'money.py')
gateway = _load_services_module('gateway', 'gateway.py')


class _Config:
    gateway_base_url = 'https://fts-uat.cardconnect.com/cardconnect/rest/'
    gateway_username = 'testing'
    gateway_password = 'testing123'


class TestGatewayRefundDecision(unittest.TestCase):
    def test_choose_void_when_unsettled(self):
        self.assertEqual(gateway.choose_refund_operation({'setlstat': '0'}), 'void')

    def test_choose_refund_when_settled(self):
        self.assertEqual(gateway.choose_refund_operation({'setlstat': 'Y'}), 'refund')

    def test_void_or_refund_uses_void_path(self):
        client = gateway.CardPointeGatewayClient(_Config())
        client.inquire = lambda retref, merchid: {'ok': True, 'data': {'setlstat': '0'}}
        client.void = lambda merchid, retref: {'ok': True, 'data': {'respstat': 'A', 'respcode': '000', 'retref': 'V123', 'resptext': 'Voided'}}
        client.refund = lambda merchid, retref, amount: {'ok': False, 'data': {}}

        result = client.void_or_refund('800000009875', '343005123105', 1.00)
        self.assertTrue(result['ok'])
        self.assertEqual(result['operation'], 'void')
        self.assertEqual(result['retref'], 'V123')

    def test_void_or_refund_uses_refund_path(self):
        client = gateway.CardPointeGatewayClient(_Config())
        client.inquire = lambda retref, merchid: {'ok': True, 'data': {'setlstat': 'Y'}}
        client.refund = lambda merchid, retref, amount: {'ok': True, 'data': {'respstat': 'A', 'respcode': '000', 'retref': 'R123', 'resptext': 'Refunded'}}
        client.void = lambda merchid, retref: {'ok': False, 'data': {}}

        result = client.void_or_refund('800000009875', '343005123105', 1.00)
        self.assertTrue(result['ok'])
        self.assertEqual(result['operation'], 'refund')
        self.assertEqual(result['retref'], 'R123')


if __name__ == '__main__':
    unittest.main()
