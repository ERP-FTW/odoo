from odoo import _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import UserError
from odoo.http import request, route


class WebsiteSalePackaging(WebsiteSale):

    def _normalize_packaging_vals(self, order, product_id, add_qty, set_qty, kwargs):
        product = request.env['product.product'].browse(int(product_id)).exists()
        website_packaging_id = kwargs.get('website_packaging_id')
        website_packaging_qty = kwargs.get('website_packaging_qty')

        if product.product_tmpl_id.website_packaging_sale_mode == 'packaging_only' and not website_packaging_id:
            default_packaging = product.product_tmpl_id._get_default_website_sale_packaging()
            if not default_packaging:
                raise UserError(_('This product can only be sold by package on eCommerce.'))
            website_packaging_id = default_packaging.id
            qty = set_qty if set_qty not in (None, '', 0, '0') else add_qty
            website_packaging_qty = float(qty or 1)

        if website_packaging_id:
            packaging = order._get_valid_website_packaging(product, website_packaging_id)
            pkg_qty = float(website_packaging_qty if website_packaging_qty not in (None, '') else 0)
            if pkg_qty < 0:
                raise UserError(_('Package quantity must be positive.'))
            if pkg_qty == 0 and float(set_qty or 0) == 0 and float(add_qty or 0) == 0:
                return add_qty, set_qty, kwargs
            kwargs.update({'website_packaging_id': packaging.id, 'website_packaging_qty': pkg_qty})
            unit_qty = packaging.qty * pkg_qty
            if set_qty not in (None, ''):
                set_qty = unit_qty
            else:
                add_qty = unit_qty
        return add_qty, set_qty, kwargs

    @route(['/shop/cart/update'], type='http', auth='public', methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kwargs):
        order = request.website.sale_get_order(force_create=True)
        add_qty, set_qty, kwargs = self._normalize_packaging_vals(order, product_id, add_qty, set_qty, kwargs)
        return super().cart_update(product_id=product_id, add_qty=add_qty, set_qty=set_qty, **kwargs)

    @route(['/shop/cart/update_json'], type='json', auth='public', methods=['POST'], website=True)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True, **kwargs):
        order = request.website.sale_get_order(force_create=True)
        add_qty, set_qty, kwargs = self._normalize_packaging_vals(order, product_id, add_qty, set_qty, kwargs)
        return super().cart_update_json(
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
            display=display,
            **kwargs,
        )
