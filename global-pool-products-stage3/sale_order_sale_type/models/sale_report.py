from odoo import models, fields

class SaleReport(models.Model):
    _inherit = 'sale.report'

    sale_type_id = fields.Many2one('sale.type', string='Sale Type', readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['sale_type_id'] = 's.sale_type_id'
        return res

    def _group_by_additional_fields(self):
        return super()._group_by_additional_fields() + ['s.sale_type_id']