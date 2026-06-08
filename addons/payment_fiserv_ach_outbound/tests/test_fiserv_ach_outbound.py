from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestFiservACHOutbound(TransactionCase):
    def setUp(self):
        super().setUp()
        usd = self.env.ref('base.USD')
        self.provider = self.env['payment.provider'].create({
            'name': 'Fiserv ACH', 'code': 'fiserv_ach_outbound', 'state': 'enabled',
            'fiserv_ach_base_url': 'https://example.test', 'fiserv_ach_merchid': 'MID1',
        })
        self.partner = self.env['res.partner'].create({'name': 'Vendor'})
        self.bank = self.env['res.partner.bank'].create({
            'acc_number': '1234567890', 'partner_id': self.partner.id, 'allow_outbound_ach': True,
            'ach_account_type': 'ECHK', 'bank_aba': '021000021',
        })
        self.tx = self.env['payment.transaction'].create({
            'provider_id': self.provider.id, 'reference': 'ACH-TX-1', 'amount': 10,
            'currency_id': usd.id, 'partner_id': self.partner.id, 'operation': 'offline',
            'is_outbound_payout': True,
        })

    def test_non_usd_validation(self):
        eur = self.env.ref('base.EUR')
        payment = self.env['account.payment'].new({'currency_id': eur.id})
        with self.assertRaises(UserError):
            self.tx._fiserv_validate_before_send(payment, self.provider)

    @patch('odoo.addons.payment_fiserv_ach_outbound.models.fiserv_ach_client.requests.post')
    def test_pending_on_approved(self, post):
        mock_resp = post.return_value
        mock_resp.text = '{"respcode": "00", "retref": "R1"}'
        mock_resp.json.return_value = {'respcode': '00', 'retref': 'R1'}
        mock_resp.raise_for_status.return_value = None
