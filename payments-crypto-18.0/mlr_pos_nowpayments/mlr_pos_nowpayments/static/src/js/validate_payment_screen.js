/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.pos.get_order();
        const paymentLines = order?.payment_ids || [];

        for (const line of paymentLines) {
            if (
                line.is_crypto_payment &&
                line.payment_method_id?.use_payment_terminal === "now" &&
                line.get_payment_status() !== "done"
            ) {
                let apiResp;
                try {
                    apiResp = await this.pos.data.call("pos.payment.method", "now_check_payment_status", [
                        {
                            invoice_id: line.cryptopay_invoice_id,
                            pm_id: line.payment_method_id.id,
                            order_id: order.uuid || order.name,
                        },
                    ]);
                } catch {
                    this.dialog.add(AlertDialog, {
                        title: _t("Payment Status Error"),
                        body: _t("Could not verify NowPayments status. Please retry."),
                    });
                    return;
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
                } else {
                    this.dialog.add(AlertDialog, {
                        title: _t("Payment Request Unpaid"),
                        body: `${_t("Payment must be finished before validating.")} ${_t("Status")}: ${apiResp?.payment_status || "unknown"}`,
                    });
                    return;
                }
            }
        }

        await super.validateOrder(isForceValidate);
    },
});
