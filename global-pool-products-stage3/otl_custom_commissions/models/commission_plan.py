from odoo import models, fields

class CommissionPlanAchievement(models.Model):
    _inherit = 'sale.commission.plan.achievement'

    customer_id = fields.Many2one('res.partner', string='Customer')
    product_id = fields.Many2one('product.product', string='Product', help="Specific product for this commission rate")
    product_categ_id = fields.Many2one('product.category', string='Product Category',
                                       help="Product category for this commission rate")
    type = fields.Selection(selection_add=[
        ('amount_paid', 'Amount Paid')
    ], required=True, ondelete={'amount_paid': 'cascade'})

    rate = fields.Float("Rate", default=0.05, required=True)