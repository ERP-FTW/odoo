from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_packaging_sale_mode = fields.Selection([
        ('unit_and_packaging', 'Allow units and packages'),
        ('packaging_only', 'Packages only'),
    ], default='unit_and_packaging', string='eCommerce Package Sale Mode')

    def _get_website_sale_packagings(self):
        self.ensure_one()
        return self.packaging_ids.filtered('website_published').sorted(
            key=lambda p: (p.website_sequence, p.sequence, p.id)
        )

    def _get_default_website_sale_packaging(self):
        self.ensure_one()
        packagings = self._get_website_sale_packagings()
        return packagings.filtered('website_default')[:1] or packagings[:1]
