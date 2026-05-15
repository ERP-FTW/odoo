import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_valid_website_packaging(self, product, website_packaging_id):
        packaging = self.env['product.packaging'].browse(int(website_packaging_id)).exists()
        if not packaging:
            raise UserError(_('Selected package does not exist.'))
        if packaging.product_id != product:
            raise UserError(_('Selected package does not belong to product %s.') % product.display_name)
        if not packaging.website_published:
            raise UserError(_('Selected package is not available on eCommerce.'))
        return packaging

    def _prepare_order_line_values(self, product_id, quantity, **kwargs):
        values = super()._prepare_order_line_values(product_id, quantity, **kwargs)
        website_packaging_id = kwargs.get('website_packaging_id')
        website_packaging_qty = kwargs.get('website_packaging_qty')
        if website_packaging_id:
            product = self.env['product.product'].browse(values['product_id'])
            packaging = self._get_valid_website_packaging(product, website_packaging_id)
            pkg_qty = float(website_packaging_qty or 0)
            unit_qty = packaging.qty * pkg_qty
            values.update({
                'product_packaging_id': packaging.id,
                'product_packaging_qty': pkg_qty,
                'product_uom_qty': unit_qty,
            })
            _logger.info('Cart create line order=%s product=%s packaging=%s pkg_qty=%s unit_qty=%s', self.name or self.id, product.display_name, packaging.name, pkg_qty, unit_qty)
        return values

    def _cart_update_order_line(self, product_id, quantity, order_line, **kwargs):
        line = super()._cart_update_order_line(product_id, quantity, order_line, **kwargs)
        if not line:
            return line
        website_packaging_id = kwargs.get('website_packaging_id')
        website_packaging_qty = kwargs.get('website_packaging_qty')
        updates = {}
        if website_packaging_id:
            packaging = self._get_valid_website_packaging(line.product_id, website_packaging_id)
            pkg_qty = float(website_packaging_qty if website_packaging_qty is not None else quantity / packaging.qty)
            updates = {
                'product_packaging_id': packaging.id,
                'product_packaging_qty': pkg_qty,
                'product_uom_qty': packaging.qty * pkg_qty,
            }
        elif line.product_packaging_id and not kwargs.get('keep_packaging'):
            updates = {'product_packaging_id': False, 'product_packaging_qty': 0.0}

        if updates:
            before = (line.product_packaging_id.id, line.product_packaging_qty)
            line.write(updates)
            after = (line.product_packaging_id.id, line.product_packaging_qty)
            _logger.info('Cart update line=%s order=%s product=%s packaging %s -> %s qty=%s', line.id, self.name or self.id, line.product_id.display_name, before, after, line.product_uom_qty)
            if before != after and self.id:
                package_txt = line.product_packaging_id and _('%s × %s = %s %s') % (
                    line.product_packaging_qty, line.product_packaging_id.display_name, line.product_uom_qty, line.product_uom.name
                ) or _('Units mode')
                self.message_post(body=_('Website package selection: Product %(product)s, %(package)s.', product=line.product_id.display_name, package=package_txt))
        return line

    def _cart_find_product_line(self, product_id, line_id=None, **kwargs):
        lines = super()._cart_find_product_line(product_id, line_id=line_id, **kwargs)
        if line_id:
            return lines
        website_packaging_id = kwargs.get('website_packaging_id')
        if website_packaging_id:
            return lines.filtered(lambda l: l.product_packaging_id.id == int(website_packaging_id))
        return lines.filtered(lambda l: not l.product_packaging_id)
