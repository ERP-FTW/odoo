import os
import sys
import unittest

CURRENT_DIR = os.path.dirname(__file__)
ADDONS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))
if ADDONS_DIR not in sys.path:
    sys.path.insert(0, ADDONS_DIR)

from cardpointe_api_base.services.http import safe_log_headers
from cardpointe_api_base.services.money import dollars_to_implied_cents


class TestCardPointeServicesSmoke(unittest.TestCase):

    def test_dollars_to_implied_cents(self):
        self.assertEqual(dollars_to_implied_cents('1.00'), '100')
        self.assertEqual(dollars_to_implied_cents('10.235'), '1024')

    def test_safe_log_headers(self):
        headers = {
            'Authorization': 'Basic abc1234567890',
            'X-CardConnect-SessionKey': 'supersecretkeyvalue',
            'Accept': 'application/json',
        }
        safe = safe_log_headers(headers)
        self.assertTrue(str(safe['Authorization']).startswith('masked:'))
        self.assertTrue(str(safe['X-CardConnect-SessionKey']).startswith('masked:'))
        self.assertEqual(safe['Accept'], 'application/json')


if __name__ == '__main__':
    unittest.main()
