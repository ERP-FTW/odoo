from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosTipCashout(models.Model):
    _name = 'pos.tip.cashout'
    _description = 'POS Tip Cashout / Tip Declaration'
    _order = 'create_date desc'

    company_id = fields.Many2one('res.company', related='session_id.company_id', store=True, readonly=True)
    session_id = fields.Many2one('pos.session', required=True, ondelete='cascade')
    config_id = fields.Many2one('pos.config', related='session_id.config_id', store=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    currency_id = fields.Many2one('res.currency', related='session_id.currency_id', readonly=True)
    pos_card_tips = fields.Monetary(readonly=True)
    pos_cash_tips = fields.Monetary(readonly=True)
    declared_cash_tips = fields.Monetary(string='Declared Cash Tips')
    card_tips_paid_from_drawer = fields.Monetary()
    card_tips_remaining = fields.Monetary(compute='_compute_remaining', store=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('paid', 'Paid'), ('cancelled', 'Cancelled')], default='draft')
    statement_line_id = fields.Many2one('account.bank.statement.line', readonly=True, copy=False)

    _sql_constraints = [
        ('employee_session_unique', 'unique(session_id, employee_id)', 'Only one tip cashout per employee is allowed for a POS session.'),
    ]

    @api.depends('pos_card_tips', 'card_tips_paid_from_drawer')
    def _compute_remaining(self):
        for cashout in self:
            cashout.card_tips_remaining = cashout.pos_card_tips - cashout.card_tips_paid_from_drawer

    def action_paid_from_drawer(self):
        for cashout in self:
            if cashout.statement_line_id:
                raise UserError('This cashout already has a drawer payout.')
            if float_compare(cashout.card_tips_paid_from_drawer, 0, precision_rounding=cashout.currency_id.rounding) <= 0:
                raise UserError('Enter a positive drawer payout amount.')
            reason = 'Tip payout - %s' % cashout.employee_id.name
            cashout.session_id.try_cash_in_out('out', cashout.card_tips_paid_from_drawer, reason, {
                'translatedType': 'out',
                'employee_id': cashout.employee_id.id,
            })
            line = self.env['account.bank.statement.line'].search([
                ('pos_session_id', '=', cashout.session_id.id),
                ('amount', '=', -cashout.card_tips_paid_from_drawer),
                ('employee_id', '=', cashout.employee_id.id),
            ], order='id desc', limit=1)
            cashout.write({'statement_line_id': line.id, 'state': 'paid'})
