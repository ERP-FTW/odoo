/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.WebsiteSalePackagingSelector = publicWidget.Widget.extend({
    selector: '.o_wsale_packaging_selector',
    events: {
        'change #website_packaging_selector': '_onPackagingChange',
        'change input[name="add_qty"]': '_onQtyChange',
    },

    start() {
        this._syncPackagingState();
        return this._super(...arguments);
    },

    _onPackagingChange() {
        this._syncPackagingState();
    },

    _onQtyChange() {
        this._syncPackagingQty();
    },

    _syncPackagingState() {
        const $select = this.$('#website_packaging_selector');
        const selectedId = $select.val();
        const packagingOnly = Boolean(parseInt(this.$el.data('packaging-only'), 10));
        if (packagingOnly && !selectedId) {
            $select.prop('selectedIndex', 0);
        }
        const finalSelectedId = $select.val();
        this.$('input[name="website_packaging_id"]').val(finalSelectedId || '');
        this._syncPackagingQty();
        const option = $select.find('option:selected');
        const label = option.text().trim();
        const packageQty = parseFloat(option.data('package-qty') || 0);
        if (finalSelectedId) {
            this.$('.o_wsale_packaging_help').text(`Sold as: ${label}. Quantity is number of packages.`);
        } else {
            this.$('.o_wsale_packaging_help').text('Quantity is number of units.');
        }
        this.$('input[name="website_packaging_qty"]').val(this.$('input[name="add_qty"]').val() || 1);
    },

    _syncPackagingQty() {
        const packagingId = this.$('input[name="website_packaging_id"]').val();
        if (packagingId) {
            this.$('input[name="website_packaging_qty"]').val(this.$('input[name="add_qty"]').val() || 1);
        } else {
            this.$('input[name="website_packaging_qty"]').val('');
        }
    },
});
