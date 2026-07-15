from odoo import _, models
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_policy_batch_for_summary(self, policy):
        self.ensure_one()
        return self.env['pos.tip.pool.batch'].search([
            ('policy_id', '=', policy.id), ('session_id', '=', self.id),
            ('state', 'in', ('calculated', 'move_created', 'approved', 'posted')),
        ], order='id desc', limit=1)

    def get_policy_adjusted_tip_summary(self, employee_id=None):
        self.ensure_one()
        base_summary = super().get_tip_cashout_summary(employee_id=employee_id)
        policy = self.env['pos.tip.policy']._get_active_policy_for_session(self)
        if not policy:
            return base_summary
        batch = self._get_policy_batch_for_summary(policy)
        contribution_by_employee = {}
        distribution_by_employee = {}
        if batch:
            contribution_by_employee = {line.employee_id.id: line.amount for line in batch.contribution_ids}
            distribution_by_employee = {line.employee_id.id: line.amount for line in batch.distribution_ids}
        for line in base_summary:
            gross = line.get('pos_card_tips', 0.0)
            paid = line.get('card_tips_paid_from_drawer', 0.0)
            contribution = contribution_by_employee.get(line.get('employee_id'), 0.0)
            distribution = distribution_by_employee.get(line.get('employee_id'), 0.0)
            if policy.require_policy_before_cashout and not batch:
                net_remaining = 0.0
                blocked = True
                message = _('A tip policy applies to this POS session. Calculate the policy batch before paying card tips from the drawer.')
            else:
                net_remaining = self.currency_id.round(max(gross - contribution + distribution - paid, 0.0))
                blocked = not policy.allow_session_cashout
                message = _('This policy does not allow session drawer cashout for policy-controlled tips.') if blocked else False
            line.update({
                'policy_applies': True,
                'policy_id': policy.id,
                'policy_name': policy.name,
                'policy_batch_id': batch.id if batch else False,
                'policy_batch_calculated': bool(batch),
                'policy_contribution_amount': contribution,
                'policy_distribution_amount': distribution,
                'policy_allow_session_cashout': policy.allow_session_cashout,
                'policy_cashout_blocked': blocked,
                'policy_cashout_block_message': message,
                'gross_card_tips': gross,
                'prior_card_tips_paid_from_drawer': paid,
                'net_card_tips_available_for_cashout': net_remaining,
                'card_tips_remaining': net_remaining,
            })
        return base_summary

    def get_tip_cashout_summary(self, employee_id=None):
        if self.env.context.get('pos_tip_policy_skip'):
            return super().get_tip_cashout_summary(employee_id=employee_id)
        self.ensure_one()
        return self.get_policy_adjusted_tip_summary(employee_id=employee_id)

    def create_tip_cashout(self, session_id, employee_id, declared_cash_tips=0.0, card_tips_paid_from_drawer=0.0):
        session = self.browse(session_id).exists()
        if session:
            policy = self.env['pos.tip.policy']._get_active_policy_for_session(session)
            if policy:
                summary = session.get_policy_adjusted_tip_summary(employee_id=employee_id)
                line = next((item for item in summary if item['employee_id'] == employee_id), None)
                if not line:
                    raise UserError(_('No policy-adjusted tips found for this employee in this session.'))
                if line.get('policy_cashout_blocked'):
                    raise UserError(line.get('policy_cashout_block_message') or _('Tip cashout is blocked by the active policy.'))
                if session.currency_id.compare_amounts(card_tips_paid_from_drawer, line.get('net_card_tips_available_for_cashout', 0.0)) > 0:
                    raise UserError(_('The payout cannot exceed the policy-adjusted net card tips available.'))
        return super().create_tip_cashout(session_id, employee_id, declared_cash_tips, card_tips_paid_from_drawer)
