/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { BillScreen } from "@pos_restaurant/app/bill_screen/bill_screen";

patch(PosPayment.prototype, {
    //exports as JSON for receipt printing
    export_for_printing(baseUrl, headerData) {
        console.log('checking if it call this export_for_printing');
        console.error('lets print all values');
        console.log(this.cryptopay_payment_link_qr_code);
        console.log(this.conversion_rate);
        let data = super.export_for_printing(baseUrl, headerData);
        data.cryptopay_payment_link_qr_code = this.cryptopay_payment_link_qr_code;
        data.conversion_rate = this.conversion_rate;
        data.invoiced_crypto_amount = this.invoiced_crypto_amount;
        return data;    
    },
    setup(vals) {
        super.setup(...arguments);
        console.log('called from new setup()');
        console.log(vals);
        try {
            this.is_crypto_payment = vals.is_crypto_payment;
            console.log('is_crypto_payment:'+vals.is_crypto_payment)
            this.cryptopay_invoice_id = vals.cryptopay_invoice_id;
            this.cryptopay_payment_link = vals.cryptopay_payment_link;
            this.cryptopay_payment_type = vals.cryptopay_payment_type;
            this.conversion_rate = vals.conversion_rate;
            const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
            let qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(vals.cryptopay_payment_link, 150, 150));
            this.cryptopay_payment_link_qr_code = "data:image/svg+xml;base64,"+ window.btoa(qr_code_svg);
            this.invoiced_crypto_amount = vals.invoiced_crypto_amount;
        }
        catch (error) {
            console.log(error);
            return false;
        }
    },
});

patch(PosStore.prototype, {
    async clickShowReceipt() {
        this.dialog.add(BillScreen);
    }
});