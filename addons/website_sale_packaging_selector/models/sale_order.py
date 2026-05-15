import logging

from odoo import models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_valid_website_packaging(self, product_id, website_packaging_id):
        packaging = self.env['product.packaging'].browse(int(website_packaging_id)).exists()
        if not packaging:
            raise UserError(_('The selected package does not exist.'))
        if packaging.product_id.id != int(product_id):
            raise UserError(_('The selected package does not match the selected product.'))
        if not packaging.website_sale_selectable:
            raise UserError(_('The selected package is not available on eCommerce.'))
        return packaging

    def _cart_find_product_line(self, product_id, line_id=None, linked_line_id=False, no_variant_attribute_value_ids=None, **kwargs):
        lines = super()._cart_find_product_line(
            product_id,
            line_id=line_id,
            linked_line_id=linked_line_id,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids,
            **kwargs,
        )
        if line_id:
            return lines
        website_packaging_id = kwargs.get('website_packaging_id')
        if website_packaging_id:
            return lines.filtered(lambda l: l.product_packaging_id.id == int(website_packaging_id))
        return lines.filtered(lambda l: not l.product_packaging_id)

    def _prepare_order_line_values(self, product_id, quantity, **kwargs):
        values = super()._prepare_order_line_values(product_id, quantity, **kwargs)
        website_packaging_id = kwargs.get('website_packaging_id')
        if website_packaging_id:
            packaging = self._get_valid_website_packaging(product_id, website_packaging_id)
            package_qty = float(kwargs.get('website_packaging_qty') or 0)
            if package_qty <= 0:
                raise UserError(_('Package quantity must be strictly positive.'))
            unit_qty = packaging.qty * package_qty
            values.update({
                'product_packaging_id': packaging.id,
                'product_packaging_qty': package_qty,
                'product_uom_qty': unit_qty,
            })
            _logger.info(
                'website_sale_packaging_selector cart create order=%s product=%s packaging=%s package_qty=%s unit_qty=%s',
                self.id, product_id, packaging.id, package_qty, unit_qty,
            )
        return values

    def _prepare_order_line_update_values(self, order_line, quantity, **kwargs):
        values = super()._prepare_order_line_update_values(order_line, quantity, **kwargs)
        website_packaging_id = kwargs.get('website_packaging_id')
        if order_line.product_packaging_id or website_packaging_id:
            packaging = order_line.product_packaging_id
            if website_packaging_id:
                packaging = self._get_valid_website_packaging(order_line.product_id.id, website_packaging_id)
            package_qty = float(kwargs.get('website_packaging_qty') or 0)
            if float_is_zero(quantity, precision_rounding=order_line.product_uom.rounding) or quantity <= 0:
                return values
            if package_qty <= 0 and packaging:
                package_qty = quantity / packaging.qty
            if package_qty <= 0:
                raise UserError(_('Package quantity must be strictly positive.'))
            unit_qty = packaging.qty * package_qty
            values.update({
                'product_packaging_id': packaging.id,
                'product_packaging_qty': package_qty,
                'product_uom_qty': unit_qty,
            })
            _logger.info(
                'website_sale_packaging_selector cart update order=%s line=%s product=%s packaging=%s package_qty=%s unit_qty=%s',
                self.id, order_line.id, order_line.product_id.id, packaging.id, package_qty, unit_qty,
            )
        return values
