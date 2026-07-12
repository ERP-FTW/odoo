from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_tip_line_total(self, order):
        tip_product = order.config_id.tip_product_id
        if not tip_product:
            return 0.0
        return sum(order.lines.filtered(lambda line: line.product_id == tip_product).mapped('price_subtotal_incl'))

    def _get_tip_employee_key(self, order):
        return order.employee_id.id or False

    def get_tip_cashout_summary(self, employee_id=None):
        self.ensure_one()
        groups = defaultdict(lambda: {
            'employee_id': False,
            'employee_name': _('Unassigned / Generic User'),
            'pos_card_tips': 0.0,
            'pos_cash_tips': 0.0,
            'declared_cash_tips': 0.0,
            'card_tips_paid_from_drawer': 0.0,
            'card_tips_remaining': 0.0,
            'ambiguous_order_ids': [],
            'mismatch_order_ids': [],
        })
        orders = self.order_ids.filtered(lambda order: order.state not in ('draft', 'cancel'))
        if employee_id:
            orders = orders.filtered(lambda order: order.employee_id.id == employee_id)
        for order in orders:
            tip_amount = order.tip_amount or 0.0
            if not tip_amount:
                continue
            key = self._get_tip_employee_key(order)
            group = groups[key]
            if order.employee_id:
                group.update({'employee_id': order.employee_id.id, 'employee_name': order.employee_id.name})
            tip_line_total = self._get_tip_line_total(order)
            if self.currency_id.compare_amounts(tip_amount, tip_line_total) != 0:
                group['mismatch_order_ids'].append(order.id)
            payments = order.payment_ids.filtered(lambda payment: not payment.is_change)
            if len(payments) > 1 and not any(payments.mapped('tip_amount')):
                group['ambiguous_order_ids'].append(order.id)
                continue
            for payment in payments:
                payment_tip = payment.tip_amount
                if not payment_tip and len(payments) == 1:
                    payment_tip = tip_amount
                if payment.payment_method_id.is_cash_count:
                    group['pos_cash_tips'] += payment_tip
                else:
                    group['pos_card_tips'] += payment_tip
        cashouts = self.env['pos.tip.cashout'].search([('session_id', '=', self.id)])
        for cashout in cashouts:
            key = cashout.employee_id.id
            group = groups[key]
            group.update({
                'employee_id': cashout.employee_id.id,
                'employee_name': cashout.employee_id.name,
                'declared_cash_tips': cashout.declared_cash_tips,
                'card_tips_paid_from_drawer': cashout.card_tips_paid_from_drawer,
                'card_tips_remaining': cashout.card_tips_remaining,
                'cashout_id': cashout.id,
                'state': cashout.state,
            })
        for group in groups.values():
            if 'cashout_id' not in group:
                group['card_tips_remaining'] = group['pos_card_tips']
                group['state'] = False
        return sorted(groups.values(), key=lambda group: (not group['employee_id'], group['employee_name']))

    @api.model
    def create_tip_cashout(self, session_id, employee_id, declared_cash_tips=0.0, card_tips_paid_from_drawer=0.0):
        session = self.browse(session_id).exists()
        if not session:
            raise UserError(_('POS session not found.'))
        summary = session.get_tip_cashout_summary(employee_id=employee_id)
        employee_summary = next((line for line in summary if line['employee_id'] == employee_id), None)
        if not employee_summary:
            raise UserError(_('No tips found for this employee in this session.'))
        cashout = self.env['pos.tip.cashout'].search([('session_id', '=', session.id), ('employee_id', '=', employee_id)], limit=1)
        vals = {
            'session_id': session.id,
            'employee_id': employee_id,
            'pos_card_tips': employee_summary['pos_card_tips'],
            'pos_cash_tips': employee_summary['pos_cash_tips'],
            'declared_cash_tips': declared_cash_tips,
            'card_tips_paid_from_drawer': card_tips_paid_from_drawer,
            'state': 'approved',
        }
        if cashout:
            cashout.write(vals)
        else:
            cashout = self.env['pos.tip.cashout'].create(vals)
        if card_tips_paid_from_drawer:
            cashout.action_paid_from_drawer()
        return cashout.id
