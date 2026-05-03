/** @odoo-module **/

import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";

export class NowPaymentsPaymentInterface extends PaymentInterface {
    async send_payment_request(uuid) {
        const order = this.pos.get_order();
        const line = order?.payment_ids?.find((paymentLine) => paymentLine.uuid === uuid);
        if (!order || !line) {
            return false;
        }

        line.set_payment_status("cryptowaiting");

        let data;
        try {
            data = await this.pos.data.call("pos.payment.method", "create_crypto_invoice", [
                {
                    pm_id: line.payment_method_id.id,
                    amount: line.amount,
                    order_id: order.uuid || order.name,
                },
            ]);
        } catch {
            line.update({ crypto_payment_status: "Invoice creation failed" });
            line.set_payment_status("retry");
            return false;
        }

        if (!data || String(data.code) !== "0") {
            line.update({ crypto_payment_status: `Invoice creation failed: ${data?.code || "unknown error"}` });
            line.set_payment_status("retry");
            return false;
        }

        const updates = {
            is_crypto_payment: true,
            cryptopay_payment_link: data.cryptopay_payment_link,
            cryptopay_invoice_id: data.invoice_id,
            conversion_rate: data.conversion_rate,
            invoiced_crypto_amount: data.crypto_amt,
            crypto_payment_status: "Invoice created",
        };

        if (data.cryptopay_payment_link && window.ZXing?.BrowserQRCodeSvgWriter) {
            const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
            const qrCodeSvg = new XMLSerializer().serializeToString(
                codeWriter.write(data.cryptopay_payment_link, 150, 150)
            );
            updates.cryptopay_payment_link_qr_code = `data:image/svg+xml;base64,${window.btoa(qrCodeSvg)}`;
        }

        line.update(updates);
        Object.assign(line, updates);

        return this._poll_payment_status(order, line);
    }

    async _poll_payment_status(order, line) {
        for (let attempt = 1; attempt <= 100; attempt++) {
            line.update({ crypto_payment_status: `Checking invoice status ${attempt}/100` });
            line.set_payment_status("cryptowaiting");

            let apiResp;
            try {
                apiResp = await this.pos.data.call("pos.payment.method", "now_check_payment_status", [
                    {
                        invoice_id: line.cryptopay_invoice_id || false,
                        pm_id: line.payment_method_id.id,
                        order_id: order.uuid || order.name,
                    },
                ]);
            } catch {
                line.set_payment_status("retry");
                line.update({ crypto_payment_status: "Status check failed" });
                return false;
            }

            if (apiResp?.payment_status === "finished") {
                const invoicedAmount = apiResp.pay_amount || line.invoiced_crypto_amount;
                line.update({
                    invoiced_crypto_amount: invoicedAmount,
                    cryptopay_payment_type: apiResp.pay_currency || line.cryptopay_payment_type,
                    conversion_rate: invoicedAmount ? Number(line.amount / invoicedAmount).toFixed(2) : line.conversion_rate,
                    crypto_payment_status: "Invoice paid",
                });
                line.set_payment_status("done");
                return true;
            }

            if (["expired", "failed", "refunded"].includes(apiResp?.payment_status)) {
                line.update({ crypto_payment_status: `Invoice ${apiResp.payment_status}` });
                line.set_payment_status("retry");
                return false;
            }

            await new Promise((resolve) => setTimeout(resolve, 5000));
        }

        line.update({ crypto_payment_status: "Invoice not confirmed" });
        line.set_payment_status("retry");
        return false;
    }

    async send_payment_cancel(order, uuid) {
        const paymentLine = order?.payment_ids?.find((line) => line.uuid === uuid);
        if (paymentLine) {
            paymentLine.update({ crypto_payment_status: "Invoice cancelled" });
            paymentLine.set_payment_status("retry");
        }
        return true;
    }
}

register_payment_method("now", NowPaymentsPaymentInterface);
