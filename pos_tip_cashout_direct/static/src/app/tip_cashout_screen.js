import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

export class TipCashoutScreen extends Component {
    static template = "pos_tip_cashout_direct.TipCashoutScreen";
    static props = {};
    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({ lines: [], drawerBalance: 0 });
        onWillStart(() => this.loadSummary());
    }
    async loadSummary() {
        this.state.lines = await this.orm.call("pos.session", "get_tip_cashout_summary", [[this.pos.session.id]]);
        this.state.drawerBalance = await this.orm.call("pos.session", "get_tip_cash_drawer_balance", [[this.pos.session.id]]);
    }
    get payableEmployeeLines() {
        return this.state.lines.filter((line) => line.employee_id && line.card_tips_remaining > 0);
    }
    async selectPayoutEmployee(line) {
        const payoutLines = this.payableEmployeeLines;
        if (!payoutLines.length) {
            this.notification.add(_t("There are no employee card tips available for payout."), { type: "warning" });
            return false;
        }
        return await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Select cashout recipient"),
            list: payoutLines.map((payoutLine) => ({
                id: payoutLine.employee_id,
                label: payoutLine.employee_name,
                description: _t("Remaining card tips: %s", this.env.utils.formatCurrency(payoutLine.card_tips_remaining)),
                isSelected: payoutLine.employee_id === line.employee_id,
                item: payoutLine,
            })),
        });
    }
    async pay(line) {
        if (!line.employee_id) {
            this.notification.add(_t("Unassigned tips must be reviewed in backend before payout."), { type: "warning" });
            return;
        }
        const payoutLine = await this.selectPayoutEmployee(line);
        if (!payoutLine) {
            return;
        }
        const drawerBefore = this.state.drawerBalance || 0;
        const remaining = payoutLine.card_tips_remaining || payoutLine.pos_card_tips || 0;
        if (remaining <= 0) {
            this.notification.add(_t("There are no remaining card tips to pay out for this employee."), { type: "warning" });
            return;
        }
        const amountInput = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Tip payout amount"),
            subtitle: _t("Enter the amount of card tips to pay from the cash drawer now. You may pay less than the remaining card tip balance; the unpaid amount stays as remaining liability."),
            startingValue: String(remaining),
            confirmButtonLabel: _t("Review Payout"),
            isValid: (value) => {
                const amount = this.parsePayoutAmount(value);
                return amount > 0 && amount <= remaining;
            },
            feedback: (value) => {
                const amount = this.parsePayoutAmount(value);
                if (amount <= 0) {
                    return _t("Enter an amount greater than zero.");
                }
                if (amount > remaining) {
                    return _t("The payout cannot exceed the remaining card tips.");
                }
                return false;
            },
        });
        const amount = this.parsePayoutAmount(amountInput);
        if (!amount) {
            return;
        }
        const confirmed = await ask(this.dialog, {
            title: _t("Confirm tip payout"),
            body: _t("This will create a cash-out from the POS drawer for %(employee)s.\n\nPayout amount: %(amount)s\nRemaining card tips after payout: %(remaining)s\nDrawer before payout: %(drawerBefore)s\nDrawer after payout: %(drawerAfter)s\n\nConfirm only after counting cash and handing it to the selected employee.", {
                employee: payoutLine.employee_name,
                amount: this.env.utils.formatCurrency(amount),
                remaining: this.env.utils.formatCurrency(remaining - amount),
                drawerBefore: this.env.utils.formatCurrency(drawerBefore),
                drawerAfter: this.env.utils.formatCurrency(drawerBefore - amount),
            }),
            confirmLabel: _t("Create Cash-Out"),
            cancelLabel: _t("Go Back"),
        });
        if (!confirmed) {
            return;
        }
        await this.orm.call("pos.session", "create_tip_cashout", [this.pos.session.id, payoutLine.employee_id, payoutLine.declared_cash_tips || 0, amount]);
        await this.loadSummary();
        this.notification.add(_t("Tip payout cash-out created."));
    }
    parsePayoutAmount(value) {
        return this.env.utils.parseValidFloat(String(value ?? "")) || 0;
    }
    back() { this.pos.showScreen("ProductScreen"); }
}
registry.category("pos_screens").add("TipCashoutScreen", TipCashoutScreen);
