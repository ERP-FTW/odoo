import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    website_published = fields.Boolean(string='Available on eCommerce', default=False)
    website_default = fields.Boolean(string='Default eCommerce Package', default=False)
    website_sequence = fields.Integer(string='eCommerce Sequence', default=10)

    @api.constrains('website_default', 'website_published', 'product_id')
    def _check_website_default_unique(self):
        for packaging in self.filtered('website_default'):
            if not packaging.website_published:
                raise ValidationError(_('A default eCommerce package must also be published on eCommerce.'))
            if packaging.product_id.packaging_ids.filtered(lambda p: p.website_default and p.id != packaging.id):
                raise ValidationError(_('Only one default eCommerce package is allowed per product.'))
            _logger.debug('Validated website default packaging %s for product %s', packaging.id, packaging.product_id.id)
