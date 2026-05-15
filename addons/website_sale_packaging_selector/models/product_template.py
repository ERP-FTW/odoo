from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_packaging_sale_mode = fields.Selection(
        selection=[
            ('unit_and_packaging', 'Allow units and packages'),
            ('packaging_only', 'Packages only'),
        ],
        string='eCommerce Packaging Sale Mode',
        default='unit_and_packaging',
    )

    def _get_website_sale_packagings(self):
        self.ensure_one()
        return self.packaging_ids.filtered('website_sale_selectable').sorted(
            key=lambda p: (p.website_sale_sequence, p.sequence, p.id)
        )

    def _get_default_website_sale_packaging(self):
        self.ensure_one()
        packagings = self._get_website_sale_packagings()
        default_packaging = packagings.filtered('website_sale_default')[:1]
        return default_packaging or packagings[:1]
