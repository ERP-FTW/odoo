import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/navbar/navbar";

patch(Navbar.prototype, {
    openTipCashout() {
        this.pos.showScreen("TipCashoutScreen");
    },
});
