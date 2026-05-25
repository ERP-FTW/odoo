/** @odoo-module */

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class CardPointeManualEntryPopup extends Component {
    static template = "pos_cardpointe_poc.CardPointeManualEntryPopup";
    static props = ["title", "tokenizerUrl", "allowedEcominds", "defaultEcomind", "cancelLabel", "close", "onToken"];

    setup() {
        this.state = useState({ ecomind: this.props.defaultEcomind || "E", tokenError: "" });
        this._boundHandler = (event) => this._handleMessage(event);
        onMounted(() => window.addEventListener("message", this._boundHandler));
        onWillUnmount(() => window.removeEventListener("message", this._boundHandler));
    }

    _extractToken(payload) {
        if (!payload) return "";
        if (typeof payload === "string") return "";
        return payload.token || payload.account || payload.message?.token || payload.message?.account || "";
    }

    _handleMessage(event) {
        const token = this._extractToken(event.data);
        if (!token) {
            return;
        }
        this.props.onToken({ token, ecomind: this.state.ecomind });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
