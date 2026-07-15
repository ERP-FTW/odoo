from unittest.mock import patch

from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestPosTipCashoutPolicy(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.account = cls.env['account.account'].create({
            'name': 'Tips Payable Test',
            'code': 'TIPTST',
            'account_type': 'liability_current',
            'company_ids': [(6, 0, cls.company.ids)],
        })
        cls.journal = cls.env['account.journal'].create({
            'name': 'Tip Policy Test Journal',
            'code': 'TPTJ',
            'type': 'general',
            'company_id': cls.company.id,
        })
        cls.config = cls.env['pos.config'].create({'name': 'Tip Policy POS Test', 'company_id': cls.company.id})
        cls.session = cls.env['pos.session'].create({'config_id': cls.config.id, 'user_id': cls.env.user.id})
        cls.employee = cls.env['hr.employee'].create({'name': 'Source Server', 'company_id': cls.company.id})
        cls.recipient_a = cls.env['hr.employee'].create({'name': 'Pool A', 'company_id': cls.company.id})
        cls.recipient_b = cls.env['hr.employee'].create({'name': 'Pool B', 'company_id': cls.company.id})
        cls.policy = cls.env['pos.tip.policy'].create({
            'name': '15 Percent Pool',
            'company_id': cls.company.id,
            'pos_config_ids': [(6, 0, cls.config.ids)],
            'basis': 'percent_of_employee_tips',
            'require_policy_before_cashout': True,
            'allow_session_cashout': True,
            'journal_id': cls.journal.id,
            'tip_payable_account_id': cls.account.id,
            'line_ids': [(0, 0, {
                'name': 'Pool recipients',
                'source_percent': 15.0,
                'recipient_employee_ids': [(6, 0, (cls.recipient_a | cls.recipient_b).ids)],
            })],
        })

    def _base_summary(self):
        return [{
            'employee_id': self.employee.id,
            'employee_name': self.employee.name,
            'pos_card_tips': 100.0,
            'pos_cash_tips': 0.0,
            'declared_cash_tips': 0.0,
            'card_tips_paid_from_drawer': 0.0,
            'card_tips_remaining': 100.0,
            'ambiguous_order_ids': [],
            'mismatch_order_ids': [],
        }]

    def test_policy_required_blocks_uncalculated_cashout(self):
        with patch('odoo.addons.pos_tip_cashout_direct.models.pos_session.PosSession.get_tip_cashout_summary', return_value=self._base_summary()):
            summary = self.session.get_policy_adjusted_tip_summary(self.employee.id)
        self.assertTrue(summary[0]['policy_cashout_blocked'])
        self.assertEqual(summary[0]['card_tips_remaining'], 0.0)

    def test_calculated_batch_adjusts_available_cashout(self):
        batch = self.env['pos.tip.pool.batch'].create({
            'name': 'Session pool',
            'policy_id': self.policy.id,
            'company_id': self.company.id,
            'session_id': self.session.id,
            'currency_id': self.currency.id,
        })
        with patch('odoo.addons.pos_tip_cashout_direct.models.pos_session.PosSession.get_tip_cashout_summary', return_value=self._base_summary()):
            batch.action_calculate()
            summary = self.session.get_policy_adjusted_tip_summary(self.employee.id)
        self.assertEqual(batch.total_contribution_amount, 15.0)
        self.assertEqual(len(batch.distribution_ids), 2)
        self.assertEqual(summary[0]['policy_contribution_amount'], 15.0)
        self.assertEqual(summary[0]['card_tips_remaining'], 85.0)

    def test_draft_move_is_balanced_and_not_posted(self):
        batch = self.env['pos.tip.pool.batch'].create({
            'name': 'Session pool',
            'policy_id': self.policy.id,
            'company_id': self.company.id,
            'session_id': self.session.id,
            'currency_id': self.currency.id,
        })
        with patch('odoo.addons.pos_tip_cashout_direct.models.pos_session.PosSession.get_tip_cashout_summary', return_value=self._base_summary()):
            batch.action_calculate()
        batch.action_create_draft_move()
        self.assertEqual(batch.move_id.state, 'draft')
        self.assertEqual(sum(batch.move_id.line_ids.mapped('debit')), sum(batch.move_id.line_ids.mapped('credit')))

    def test_session_cashout_disabled_blocks_payout(self):
        self.policy.allow_session_cashout = False
        batch = self.env['pos.tip.pool.batch'].create({
            'name': 'Session pool',
            'policy_id': self.policy.id,
            'company_id': self.company.id,
            'session_id': self.session.id,
            'currency_id': self.currency.id,
        })
        with patch('odoo.addons.pos_tip_cashout_direct.models.pos_session.PosSession.get_tip_cashout_summary', return_value=self._base_summary()):
            batch.action_calculate()
            with self.assertRaises(UserError):
                self.session.create_tip_cashout(self.session.id, self.employee.id, 0.0, 1.0)
