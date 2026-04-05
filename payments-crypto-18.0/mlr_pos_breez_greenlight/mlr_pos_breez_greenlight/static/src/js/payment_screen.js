/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
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
                        this.popup.add(ErrorPopup, {
                            title: _t("Payment Request Pending"),
                            body: _t("Payment pending, retry after customer confirms."),
                        });
                        line.set_payment_status("cryptowaiting");
                    } else if (["expired", "invalid", "failed"].includes(status)) {
                        this.popup.add(ErrorPopup, {
                            title: _t("Payment Request Expired"),
                            body: _t("Payment request expired, retry by sending a new request."),
                        });
                        line.set_payment_status("retry");
                    } else if (status) {
                        this.popup.add(ErrorPopup, {
                            title: _t("Payment Request Unknown"),
                            body: _t("Payment status is unknown, retry by sending a new request."),
                        });
                    }
                } catch {
                    return false;
                }
            }
        }
        return super.validateOrder(isForceValidate);
    },
});
