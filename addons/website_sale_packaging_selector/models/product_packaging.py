import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    website_sale_selectable = fields.Boolean(string='Available on eCommerce', default=False)
    website_sale_default = fields.Boolean(string='Default eCommerce Package', default=False)
    website_sale_sequence = fields.Integer(string='eCommerce Sequence', default=10)

    @api.constrains('website_sale_default', 'product_id')
    def _check_unique_website_sale_default(self):
        for packaging in self.filtered('website_sale_default'):
            duplicates = self.search([
                ('id', '!=', packaging.id),
                ('product_id', '=', packaging.product_id.id),
                ('website_sale_default', '=', True),
            ], limit=1)
            if duplicates:
                raise ValidationError(_('Only one default eCommerce package is allowed per product.'))

    @api.constrains('website_sale_default', 'website_sale_selectable')
    def _check_default_requires_selectable(self):
        for packaging in self:
            if packaging.website_sale_default and not packaging.website_sale_selectable:
                raise ValidationError(_('A default eCommerce package must be selectable on eCommerce.'))
