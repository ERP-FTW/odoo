from odoo import models, fields

class CommissionPlan(models.Model):
    _inherit = 'sale.commission.plan.achievement'

    customer_id = fields.Many2one(
        'res.partner',
        string='Customers'
    )