from odoo import fields, models


class PosTipCashout(models.Model):
    _inherit = 'pos.tip.cashout'

    policy_contribution_amount = fields.Monetary(currency_field='currency_id', readonly=True)
    policy_distribution_amount = fields.Monetary(currency_field='currency_id', readonly=True)
