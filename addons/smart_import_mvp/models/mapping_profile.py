from odoo import fields, models


class SmartImportMappingProfile(models.Model):
    _name = 'smart.import.mapping.profile'
    _description = 'Smart Import Mapping Profile'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company')
    active = fields.Boolean(default=True)
    keyword_ids = fields.One2many('smart.import.mapping.keyword', 'profile_id', string='Keywords')


class SmartImportMappingKeyword(models.Model):
    _name = 'smart.import.mapping.keyword'
    _description = 'Smart Import Mapping Keyword'
    _order = 'priority, id'

    profile_id = fields.Many2one('smart.import.mapping.profile', required=True, ondelete='cascade')
    source_key = fields.Char(required=True)
    canonical_key = fields.Selection([
        ('default_code', 'Default Code'),
        ('name', 'Name'),
        ('category', 'Category'),
        ('uom_name', 'UoM Name'),
        ('vendor_name', 'Vendor Name'),
        ('vendor_price', 'Vendor Price'),
        ('vendor_moq', 'Vendor MOQ'),
        ('vendor_uom', 'Vendor UoM'),
        ('default_location', 'Default Location'),
        ('min_stock', 'Minimum Stock'),
        ('min_production_qty', 'Minimum Production Quantity'),
        ('sell_ok', 'Can Be Sold'),
        ('buy_or_make', 'Buy Or Make'),
        ('tags', 'Tags'),
    ], required=True)
    priority = fields.Integer(default=10)
    active = fields.Boolean(default=True)
