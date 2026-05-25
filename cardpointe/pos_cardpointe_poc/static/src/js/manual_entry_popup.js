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

        let data = payload;
        if (typeof data === "string") {
            try {
                data = JSON.parse(data);
            } catch {
                return "";
            }
        }
        if (typeof data !== "object") return "";

        const candidates = [
            data,
            data.message,
            data.response,
            data.tokenizeResponse,
            data.tokenizerResponse,
        ].filter((item) => item && typeof item === "object");

        for (const candidate of candidates) {
            const token = candidate.token || candidate.account || candidate.acctid || "";
            if (token) {
                return token;
            }
        }
        return "";
    }

    async _handleMessage(event) {
        const token = this._extractToken(event.data);
        if (!token) {
            return;
        }
        try {
            await this.props.onToken({ token, ecomind: this.state.ecomind });
            this.props.close();
        } catch {
            // Keep popup open so cashier can retry tokenizer submission.
        }
    }

    cancel() {
        this.props.close();
    }
}
