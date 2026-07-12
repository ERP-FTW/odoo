import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class TipCashoutScreen extends Component {
    static template = "pos_tip_cashout_direct.TipCashoutScreen";
    static props = {};
    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ lines: [] });
        onWillStart(() => this.loadSummary());
    }
    async loadSummary() {
        this.state.lines = await this.orm.call("pos.session", "get_tip_cashout_summary", [[this.pos.session.id]]);
    }
    async pay(line) {
        if (!line.employee_id) {
            this.notification.add(_t("Unassigned tips must be reviewed in backend before payout."), { type: "warning" });
            return;
        }
        await this.orm.call("pos.session", "create_tip_cashout", [this.pos.session.id, line.employee_id, line.declared_cash_tips || 0, line.pos_card_tips]);
        await this.loadSummary();
        this.notification.add(_t("Tip payout cash-out created."));
    }
    back() { this.pos.showScreen("ProductScreen"); }
}
registry.category("pos_screens").add("TipCashoutScreen", TipCashoutScreen);
