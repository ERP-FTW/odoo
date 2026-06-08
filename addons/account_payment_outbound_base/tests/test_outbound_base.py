from odoo.tests.common import TransactionCase


class TestOutboundBase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.provider = self.env['payment.provider'].create({'name': 'Dummy', 'code': 'transfer', 'state': 'enabled'})
        self.journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        self.journal.outbound_payment_provider_id = self.provider

    def test_provider_resolution_from_journal(self):
        payment = self.env['account.payment'].new({'journal_id': self.journal.id})
        self.assertEqual(payment._get_outbound_payment_provider(), self.provider)
