/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { WebsiteSale } from '@website_sale/js/website_sale';
import { rpc } from '@web/core/network/rpc';

publicWidget.registry.WebsiteSalePackagingSelector = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    events: {
        'change #website_packaging_selector': '_onPackagingChange',
        'change .o_website_packaging_visible_qty': '_onVisibleQtyChange',
    },
    start() {
        this._syncPackagingFields();
        return this._super(...arguments);
    },
    _onPackagingChange() { this._syncPackagingFields(); },
    _onVisibleQtyChange() { this._syncPackagingFields(); },
    _syncPackagingFields() {
        const select = this.el.querySelector('#website_packaging_selector');
        const qty = this.el.querySelector('.o_website_packaging_visible_qty');
        const hiddenId = this.el.querySelector('.o_website_packaging_id');
        const hiddenQty = this.el.querySelector('.o_website_packaging_qty');
        if (!select || !qty || !hiddenId || !hiddenQty) { return; }
        const packagingId = select.value;
        hiddenId.value = packagingId;
        hiddenQty.value = packagingId ? qty.value : '';
        if (select.dataset.packagingOnly === '1' && !packagingId && select.options.length) {
            select.selectedIndex = 0;
            hiddenId.value = select.value;
            hiddenQty.value = qty.value;
        }
    },
});

WebsiteSale.include({
    _changeCartQuantity($input, value, $dom_optional, line_id, productIDs) {
        const websitePackagingId = $input.data('website-packaging-id');
        if (!websitePackagingId) {
            return this._super(...arguments);
        }
        rpc('/shop/cart/update_json', {
            line_id,
            product_id: parseInt($input.data('product-id'), 10),
            set_qty: value,
            display: true,
            website_packaging_id: websitePackagingId,
            website_packaging_qty: value,
        }).then((data) => {
            if (data.quantity !== undefined) {
                $input.val(value);
            }
            window.location.reload();
        });
    },
});
