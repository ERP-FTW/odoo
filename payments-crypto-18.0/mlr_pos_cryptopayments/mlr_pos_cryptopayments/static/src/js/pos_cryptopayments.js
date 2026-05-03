/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { BillScreen } from "@pos_restaurant/app/bill_screen/bill_screen";

patch(PosPayment.prototype, {
    export_for_printing(baseUrl, headerData) {
        const data = super.export_for_printing(baseUrl, headerData);
        data.cryptopay_payment_link_qr_code = this.cryptopay_payment_link_qr_code;
        data.conversion_rate = this.conversion_rate;
        data.invoiced_crypto_amount = this.invoiced_crypto_amount;
        data.cryptopay_payment_type = this.cryptopay_payment_type;
        data.cryptopay_payment_link = this.cryptopay_payment_link;
        return data;
    },
    setup(vals) {
        super.setup(...arguments);
        this.is_crypto_payment = Boolean(vals?.is_crypto_payment);
        this.cryptopay_invoice_id = vals?.cryptopay_invoice_id || false;
        this.cryptopay_payment_link = vals?.cryptopay_payment_link || false;
        this.cryptopay_payment_type = vals?.cryptopay_payment_type || false;
        this.conversion_rate = vals?.conversion_rate || false;
        this.cryptopay_payment_link_qr_code = vals?.cryptopay_payment_link_qr_code || false;
        this.invoiced_crypto_amount = vals?.invoiced_crypto_amount || false;
        this.crypto_payment_status = vals?.crypto_payment_status || false;

        if (!this.cryptopay_payment_link_qr_code && this.cryptopay_payment_link && window.ZXing?.BrowserQRCodeSvgWriter) {
            const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
            const qrCodeSvg = new XMLSerializer().serializeToString(
                codeWriter.write(this.cryptopay_payment_link, 150, 150)
            );
            this.cryptopay_payment_link_qr_code = `data:image/svg+xml;base64,${window.btoa(qrCodeSvg)}`;
        }
    },
});

patch(PosStore.prototype, {
    async clickShowReceipt() {
        this.dialog.add(BillScreen);
    },
});
