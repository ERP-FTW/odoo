from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosTipPolicy(models.Model):
    _name = 'pos.tip.policy'
    _description = 'POS Tip Pool Policy'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    pos_config_ids = fields.Many2many('pos.config', string='POS Configurations')
    effective_start = fields.Date()
    effective_end = fields.Date()
    basis = fields.Selection([
        ('percent_of_employee_tips', 'Percent of Employee Tips'),
        ('percent_of_selected_employee_tips', 'Percent of Selected Employee Tips'),
        ('percent_of_all_session_tips', 'Percent of All Session Tips'),
    ], required=True, default='percent_of_employee_tips')
    require_policy_before_cashout = fields.Boolean(default=True)
    allow_session_cashout = fields.Boolean(default=True)
    journal_id = fields.Many2one('account.journal', domain="[('type', '=', 'general'), ('company_id', '=', company_id)]")
    tip_payable_account_id = fields.Many2one('account.account', required=True, domain="[('company_ids', 'in', company_id)]")
    tip_pool_clearing_account_id = fields.Many2one('account.account', domain="[('company_ids', 'in', company_id)]")
    line_ids = fields.One2many('pos.tip.policy.line', 'policy_id')

    @api.constrains('effective_start', 'effective_end')
    def _check_dates(self):
        for policy in self:
            if policy.effective_start and policy.effective_end and policy.effective_start > policy.effective_end:
                raise ValidationError(_('The policy effective start must be before its effective end.'))

    def _policy_domain_for_session(self, session):
        session_date = fields.Date.to_date(session.start_at or fields.Datetime.now())
        return [
            ('active', '=', True),
            ('company_id', '=', session.company_id.id),
            '|', ('pos_config_ids', '=', False), ('pos_config_ids', 'in', session.config_id.id),
            '|', ('effective_start', '=', False), ('effective_start', '<=', session_date),
            '|', ('effective_end', '=', False), ('effective_end', '>=', session_date),
        ]

    @api.model
    def _get_active_policy_for_session(self, session):
        return self.search(self._policy_domain_for_session(session), order='id desc', limit=1)


class PosTipPolicyLine(models.Model):
    _name = 'pos.tip.policy.line'
    _description = 'POS Tip Pool Policy Line'
    _order = 'sequence, id'

    policy_id = fields.Many2one('pos.tip.policy', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    source_employee_ids = fields.Many2many('hr.employee', 'pos_tip_policy_line_source_employee_rel', 'line_id', 'employee_id')
    recipient_employee_ids = fields.Many2many('hr.employee', 'pos_tip_policy_line_recipient_employee_rel', 'line_id', 'employee_id')
    source_percent = fields.Float(default=0.0)
    distribution_percent = fields.Float(default=0.0)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
