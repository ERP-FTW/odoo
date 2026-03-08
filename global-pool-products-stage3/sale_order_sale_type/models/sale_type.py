from odoo import models, fields

class SaleType(models.Model):
    _name = 'sale.type'
    _description = 'Sale Type'

    name = fields.Char(string='Name', required=True, translate=True)
