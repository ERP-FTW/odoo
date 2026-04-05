/** @odoo-module */

import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";

const STATUS_ATTEMPTS = 3;
const STATUS_DELAY_MS = 5000;

export class PaymentBreezPayment extends PaymentInterface {
    async send_payment_request(cid) {
        const order = this.pos.get_order();
        const line = order?.get_selected_paymentline();
        if (!order || !line) {
            return false;
        }

        await super.send_payment_request(...arguments);

        let data;
        try {
            data = await this.env.services.orm.silent.call(
                "pos.payment.method",
                "breez_create_crypto_invoice",
                [{ pm_id: line.payment_method_id.id, amount: line.amount, order_id: order.uuid }]
            );
        } catch {
            return false;
        }

        if (data.code !== 0 && data.code !== "0") {
            return false;
        }

        const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
        const qrCodeSvg = new XMLSerializer().serializeToString(
            codeWriter.write(data.cryptopay_payment_link, 150, 150)
        );

        line.is_crypto_payment = true;
        line.cryptopay_payment_link = data.cryptopay_payment_link;
        line.cryptopay_payment_link_qr_code = `data:image/svg+xml;base64,${window.btoa(qrCodeSvg)}`;
        line.cryptopay_invoice_id = data.invoice_id;
        line.invoiced_crypto_amount = data.crypto_amt;
        line.cryptopay_payment_type = data.cryptopay_payment_type;
        const conversionRate = line.amount / (line.invoiced_crypto_amount / 100000000);
        line.conversion_rate = conversionRate.toFixed(2);
        line.set_payment_status("waiting");

        return this._check_payment_status(line);
    }

    async send_payment_cancel(order, cid) {
        super.send_payment_cancel(...arguments);
    }

    async _check_payment_status(line) {
        const order = this.pos.get_order();
        if (!order) {
            return false;
        }

        for (let i = 0; i < STATUS_ATTEMPTS; i++) {
            line.crypto_payment_status = `Checking Invoice status ${i + 1}/${STATUS_ATTEMPTS}`;
            try {
                const apiResp = await this.env.services.orm.silent.call(
                    "pos.payment.method",
                    "breez_check_payment_status",
                    [{
                        invoice_id: line.cryptopay_invoice_id,
                        pm_id: line.payment_method_id.id,
                        order_id: order.uuid,
                    }]
                );
                const status = (apiResp.status || "").toLowerCase();
                if (["paid", "settled", "complete"].includes(status)) {
                    line.crypto_payment_status = "Invoice Paid";
                    line.set_payment_status("done");
                    return true;
                }
                if (["expired", "invalid", "failed"].includes(status)) {
                    line.crypto_payment_status = "Invoice Expired";
                    line.set_payment_status("retry");
                    return false;
                }
            } catch {
                return false;
            }
            await new Promise((resolve) => setTimeout(resolve, STATUS_DELAY_MS));
        }

        line.set_payment_status("waiting");
        return false;
    }
}
