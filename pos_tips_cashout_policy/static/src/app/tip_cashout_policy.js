import { patch } from "@web/core/utils/patch";
import { TipCashoutScreen } from "@pos_tip_cashout_direct/app/tip_cashout_screen";

patch(TipCashoutScreen.prototype, {
    async pay(line) {
        if (line.policy_cashout_blocked) {
            this.notification.add(line.policy_cashout_block_message, { type: "warning" });
            return;
        }
        return super.pay(...arguments);
    },
});
