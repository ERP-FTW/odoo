from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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

    @api.constrains('customer_id', 'plan_id')
    def _check_unique_customer(self):
        for record in self:
            if not record.customer_id:
                continue  # skip lines without customer
            existing_lines = self.search([
                ('id', '!=', record.id),
                ('plan_id', '=', record.plan_id.id),
                ('customer_id', '=', record.customer_id.id)
            ])
            if existing_lines:
                raise ValidationError(_(
                    "Customer '%s' is already used in another line. "
                    "You cannot select the same customer multiple times in the same commission plan."
                ) % record.customer_id.display_name)
