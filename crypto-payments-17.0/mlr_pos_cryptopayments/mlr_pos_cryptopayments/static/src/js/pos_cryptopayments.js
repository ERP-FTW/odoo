/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Payment } from "@point_of_sale/app/store/models";

patch(Payment.prototype, {
    //exports as JSON for receipt printing
    export_for_printing() {
        let data = super.export_for_printing();
        data.cryptopay_payment_link_qr_code = this.cryptopay_payment_link_qr_code;
        data.conversion_rate = this.conversion_rate;
        data.invoiced_crypto_amount = this.invoiced_crypto_amount;
        return data;    
    },
    init_from_JSON(json) {
        console.log('Calling Init_from_Json for payment');
        console.log(json);
        super.init_from_JSON(...arguments);
        try {
            this.is_crypto_payment = json.is_crypto_payment;
            console.log('is_crypto_payment:'+json.is_crypto_payment)
            this.cryptopay_invoice_id = json.cryptopay_invoice_id;
            this.cryptopay_payment_link = json.cryptopay_payment_link;
            this.cryptopay_payment_type = json.cryptopay_payment_type;
            this.conversion_rate = json.conversion_rate;
            const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
            let qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(json.cryptopay_payment_link, 150, 150));
            this.cryptopay_payment_link_qr_code = "data:image/svg+xml;base64,"+ window.btoa(qr_code_svg);
            this.invoiced_crypto_amount = json.invoiced_crypto_amount;
        }
        catch (error) {
            console.log(error);
            return false;
        }
    },
    export_as_JSON() {
        let json = super.export_as_JSON(...arguments);
        console.log('super export as json');
        console.log(json)
        json.is_crypto_payment = this.is_crypto_payment;
        console.log('crypto payment type '+json.is_crypto_payment)
        json.cryptopay_payment_type = this.cryptopay_payment_type;
        json.cryptopay_invoice_id = this.cryptopay_invoice_id;
        json.cryptopay_payment_link_qr_code = this.cryptopay_payment_link_qr_code;
        json.cryptopay_payment_link = this.cryptopay_payment_link;
        json.invoiced_crypto_amount = this.invoiced_crypto_amount;
        json.conversion_rate = this.conversion_rate;
        console.log('calling export_as_JSON');
        console.log(json);
        return json;
    },
});
