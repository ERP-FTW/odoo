import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosPayment.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.tip_amount = vals.tip_amount || 0;
    },
});

patch(PosStore.prototype, {
    async set_tip(tip) {
        const order = this.get_order();
        const beforeTip = order?.tip_amount || 0;
        const result = await super.set_tip(...arguments);
        const tipDelta = (order?.tip_amount || tip || 0) - beforeTip;
        const selectedPaymentLine = order?.get_selected_paymentline?.() || order?.payment_ids?.[0];
        if (selectedPaymentLine && tipDelta) {
            selectedPaymentLine.update({ tip_amount: (selectedPaymentLine.tip_amount || 0) + tipDelta });
        }
        return result;
    },
});
