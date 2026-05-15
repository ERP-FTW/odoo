import logging

from odoo.exceptions import UserError
from odoo.http import request, route
from odoo.tools import float_compare
from odoo.tools.translate import _

from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class WebsiteSalePackagingSelector(WebsiteSale):

    def _normalize_packaging_cart_values(self, product_id, add_qty=0, set_qty=0, line_id=None, **kwargs):
        product = request.env['product.product'].browse(int(product_id)).exists()
        if not product:
            raise UserError(_('The selected product does not exist.'))

        template = product.product_tmpl_id
        website_packaging_id = kwargs.get('website_packaging_id')
        website_packaging_qty = kwargs.get('website_packaging_qty')
        packaging = request.env['product.packaging']

        if website_packaging_id:
            packaging = request.env['product.packaging'].browse(int(website_packaging_id)).exists()
            if not packaging:
                raise UserError(_('The selected package does not exist.'))
            if packaging.product_id.id != product.id:
                raise UserError(_('The selected package does not match the selected product.'))
            if not packaging.website_sale_selectable:
                raise UserError(_('The selected package is not available on eCommerce.'))

        if template.website_packaging_sale_mode == 'packaging_only' and not packaging:
            default_packaging = template._get_default_website_sale_packaging()
            if not default_packaging:
                raise UserError(_('This product can only be sold by package, but no selectable package is configured.'))
            packaging = default_packaging
            kwargs['website_packaging_id'] = packaging.id
            if website_packaging_qty is None:
                website_packaging_qty = set_qty or add_qty or 1

        if packaging:
            package_qty = float(website_packaging_qty if website_packaging_qty is not None else (set_qty or add_qty or 0))
            if line_id and float_compare(float(set_qty or 0), 0.0, precision_rounding=0.00001) == 0 and float_compare(float(add_qty or 0), 0.0, precision_rounding=0.00001) == 0:
                package_qty = 0
            if package_qty <= 0 and not (line_id and (set_qty == 0 or add_qty == 0)):
                raise UserError(_('Package quantity must be strictly positive.'))
            unit_qty = packaging.qty * package_qty
            kwargs['website_packaging_qty'] = package_qty
            add_qty = unit_qty if add_qty else add_qty
            set_qty = unit_qty if set_qty else set_qty
            _logger.info(
                'website_sale_packaging_selector controller normalize product=%s packaging=%s package_qty=%s unit_qty=%s order=%s',
                product.id, packaging.id, package_qty, unit_qty, request.website.sale_get_order().id,
            )

        return add_qty, set_qty, kwargs

    @route(['/shop/cart/update'], type='http', auth='public', methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kwargs):
        add_qty, set_qty, kwargs = self._normalize_packaging_cart_values(product_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        return super().cart_update(product_id, add_qty=add_qty, set_qty=set_qty, **kwargs)

    @route(['/shop/cart/update_json'], type='json', auth='public', methods=['POST'], website=True)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, **kwargs):
        add_qty, set_qty, kwargs = self._normalize_packaging_cart_values(
            product_id, add_qty=add_qty, set_qty=set_qty, line_id=line_id, **kwargs
        )
        return super().cart_update_json(product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
