/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        for (const line of this.paymentLines) {
            if (line.is_crypto_payment && line.payment_method_id.use_payment_terminal === "breez") {
                try {
                    const order = this.pos.get_order();
                    if (!order) {
                        return false;
                    }
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
                    } else if (["new", "unpaid", "processing", "pending"].includes(status)) {
                        line.set_payment_status("waiting");
                        return false;
                    } else if (["expired", "invalid", "failed"].includes(status)) {
                        line.set_payment_status("retry");
                        return false;
                    }
                } catch {
                    return false;
                }
            }
        }
        return super.validateOrder(isForceValidate);
    },
});
