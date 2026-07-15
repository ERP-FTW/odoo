from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class PosTipPoolBatch(models.Model):
    _name = 'pos.tip.pool.batch'
    _description = 'POS Tip Pool Batch'
    _order = 'create_date desc'

    name = fields.Char(default=lambda self: _('New'), required=True)
    policy_id = fields.Many2one('pos.tip.policy', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    session_id = fields.Many2one('pos.session')
    pos_config_ids = fields.Many2many('pos.config')
    date_start = fields.Datetime()
    date_end = fields.Datetime()
    source_employee_ids = fields.Many2many('hr.employee', 'pos_tip_pool_batch_source_employee_rel', 'batch_id', 'employee_id', compute='_compute_employee_ids', store=True)
    recipient_employee_ids = fields.Many2many('hr.employee', 'pos_tip_pool_batch_recipient_employee_rel', 'batch_id', 'employee_id', compute='_compute_employee_ids', store=True)
    contribution_ids = fields.One2many('pos.tip.pool.contribution', 'batch_id')
    distribution_ids = fields.One2many('pos.tip.pool.distribution', 'batch_id')
    move_id = fields.Many2one('account.move', readonly=True, copy=False)
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id)
    total_basis_amount = fields.Monetary(compute='_compute_totals', store=True)
    total_contribution_amount = fields.Monetary(compute='_compute_totals', store=True)
    total_distribution_amount = fields.Monetary(compute='_compute_totals', store=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('calculated', 'Calculated'), ('move_created', 'Move Created'),
        ('approved', 'Approved'), ('posted', 'Posted'), ('cancelled', 'Cancelled'), ('reversed', 'Reversed')], default='draft')

    @api.depends('contribution_ids.employee_id', 'distribution_ids.employee_id')
    def _compute_employee_ids(self):
        for batch in self:
            batch.source_employee_ids = batch.contribution_ids.mapped('employee_id')
            batch.recipient_employee_ids = batch.distribution_ids.mapped('employee_id')

    @api.depends('contribution_ids.basis_amount', 'contribution_ids.amount', 'distribution_ids.amount')
    def _compute_totals(self):
        for batch in self:
            batch.total_basis_amount = sum(batch.contribution_ids.mapped('basis_amount'))
            batch.total_contribution_amount = sum(batch.contribution_ids.mapped('amount'))
            batch.total_distribution_amount = sum(batch.distribution_ids.mapped('amount'))

    def _employee_partner(self, employee):
        return employee.work_contact_id or employee.user_id.partner_id or employee.address_home_id

    def _scope_summary(self):
        self.ensure_one()
        if self.session_id:
            return self.session_id.with_context(pos_tip_policy_skip=True).get_tip_cashout_summary()
        raise UserError(_('Date-range policy batches are not implemented for calculation in this MVP. Use a POS session.'))

    def _eligible_lines_for_policy_line(self, policy_line, summary_by_employee):
        self.ensure_one()
        if policy_line.source_employee_ids:
            return [summary_by_employee[employee.id] for employee in policy_line.source_employee_ids if employee.id in summary_by_employee]
        return list(summary_by_employee.values())

    def _round(self, amount):
        self.ensure_one()
        return self.currency_id.round(amount)

    def action_calculate(self):
        for batch in self:
            if batch.state not in ('draft', 'calculated'):
                raise UserError(_('Only draft or calculated batches can be recalculated.'))
            if batch.move_id and batch.move_id.state == 'posted':
                raise UserError(_('Posted policy batches cannot be recalculated in place.'))
            summary = batch._scope_summary()
            summary_by_employee = {line['employee_id']: line for line in summary if line.get('employee_id')}
            contributions_by_employee = defaultdict(lambda: {'basis': 0.0, 'amount': 0.0, 'percent_total': 0.0})
            recipient_percents = defaultdict(float)
            equal_recipients = self.env['hr.employee']
            for line in batch.policy_id.line_ids.filtered('active'):
                for source in batch._eligible_lines_for_policy_line(line, summary_by_employee):
                    basis = source.get('pos_card_tips', 0.0)
                    amount = batch._round(basis * line.source_percent / 100.0)
                    data = contributions_by_employee[source['employee_id']]
                    data['basis'] += basis
                    data['amount'] += amount
                    data['percent_total'] += line.source_percent
                if line.recipient_employee_ids:
                    if line.distribution_percent:
                        for employee in line.recipient_employee_ids:
                            recipient_percents[employee.id] += line.distribution_percent
                    else:
                        equal_recipients |= line.recipient_employee_ids
            if recipient_percents and float_compare(sum(recipient_percents.values()), 100.0, precision_digits=2) != 0:
                raise ValidationError(_('Distribution percentages must total 100%%.'))
            total_contribution = batch._round(sum(data['amount'] for data in contributions_by_employee.values()))
            batch.contribution_ids.unlink()
            batch.distribution_ids.unlink()
            for employee_id, data in contributions_by_employee.items():
                self.env['pos.tip.pool.contribution'].create({
                    'batch_id': batch.id, 'employee_id': employee_id, 'session_id': batch.session_id.id,
                    'basis_amount': batch._round(data['basis']), 'percent': data['percent_total'],
                    'amount': batch._round(data['amount']), 'currency_id': batch.currency_id.id,
                })
            distribution_values = []
            if recipient_percents:
                items = list(recipient_percents.items())
                running = 0.0
                for index, (employee_id, percent) in enumerate(items):
                    amount = batch._round(total_contribution * percent / 100.0)
                    if index == len(items) - 1:
                        amount = batch._round(total_contribution - running)
                    running += amount
                    distribution_values.append((employee_id, percent, amount))
            elif equal_recipients and total_contribution:
                recipients = equal_recipients
                running = 0.0
                percent = 100.0 / len(recipients)
                for index, employee in enumerate(recipients):
                    amount = batch._round(total_contribution / len(recipients))
                    if index == len(recipients) - 1:
                        amount = batch._round(total_contribution - running)
                    running += amount
                    distribution_values.append((employee.id, percent, amount))
            for employee_id, percent, amount in distribution_values:
                self.env['pos.tip.pool.distribution'].create({
                    'batch_id': batch.id, 'employee_id': employee_id, 'session_id': batch.session_id.id,
                    'amount': amount, 'distribution_percent': percent, 'currency_id': batch.currency_id.id,
                })
            if float_compare(batch.total_contribution_amount, batch.total_distribution_amount, precision_rounding=batch.currency_id.rounding) != 0:
                raise ValidationError(_('Total distributions must equal total contributions.'))
            batch.state = 'calculated'
        return True

    def action_create_draft_move(self):
        for batch in self:
            if batch.state not in ('calculated', 'move_created', 'approved'):
                raise UserError(_('Calculate the policy batch before creating a journal entry.'))
            if batch.move_id:
                continue
            journal = batch.policy_id.journal_id
            account = batch.policy_id.tip_payable_account_id
            if not journal or not account:
                raise UserError(_('Configure a journal and Tips Payable account on the policy.'))
            lines = []
            for contribution in batch.contribution_ids:
                if float_is_zero(contribution.amount, precision_rounding=batch.currency_id.rounding):
                    continue
                partner = batch._employee_partner(contribution.employee_id)
                lines.append((0, 0, {'name': _('Tip policy contribution - %s', contribution.employee_id.name), 'account_id': account.id, 'partner_id': partner.id or False, 'debit': contribution.amount, 'credit': 0.0}))
            for distribution in batch.distribution_ids:
                if float_is_zero(distribution.amount, precision_rounding=batch.currency_id.rounding):
                    continue
                partner = batch._employee_partner(distribution.employee_id)
                lines.append((0, 0, {'name': _('Tip policy distribution - %s', distribution.employee_id.name), 'account_id': account.id, 'partner_id': partner.id or False, 'debit': 0.0, 'credit': distribution.amount}))
            move = self.env['account.move'].create({'move_type': 'entry', 'journal_id': journal.id, 'date': fields.Date.context_today(batch), 'ref': batch.name, 'line_ids': lines})
            batch.move_id = move.id
            batch.state = 'move_created'
        return True

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_cancel(self):
        for batch in self:
            if batch.move_id and batch.move_id.state == 'posted':
                raise UserError(_('Cancel or reverse the posted journal entry before cancelling this batch.'))
        self.write({'state': 'cancelled'})

    def action_reverse(self):
        for batch in self:
            if batch.move_id and batch.move_id.state == 'posted':
                batch.move_id._reverse_moves(default_values_list=[{'ref': _('Reversal of %s', batch.name)}], cancel=True)
            batch.state = 'reversed'


class PosTipPoolContribution(models.Model):
    _name = 'pos.tip.pool.contribution'
    _description = 'POS Tip Pool Contribution'

    batch_id = fields.Many2one('pos.tip.pool.batch', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    session_id = fields.Many2one('pos.session')
    basis_amount = fields.Monetary(currency_field='currency_id')
    percent = fields.Float()
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', required=True)


class PosTipPoolDistribution(models.Model):
    _name = 'pos.tip.pool.distribution'
    _description = 'POS Tip Pool Distribution'

    batch_id = fields.Many2one('pos.tip.pool.batch', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    session_id = fields.Many2one('pos.session')
    amount = fields.Monetary(currency_field='currency_id')
    distribution_percent = fields.Float()
    currency_id = fields.Many2one('res.currency', required=True)
