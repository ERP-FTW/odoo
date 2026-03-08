from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    sale_type_id = fields.Many2one('sale.type', tracking=True, index=True)
