from odoo import models, fields

class CommissionPlan(models.Model):
    _inherit = 'sale.commission.plan'

    user_type = fields.Selection(
        selection_add=[('referrer_id', 'Referrer')],
        string='Based on',
        required=True,
        default='person',
        ondelete={'referrer_id': 'cascade'}
    )

    referrer_id = fields.Many2one('res.partner', 'Referrer', domain=[('grade_id', '!=', False)])
