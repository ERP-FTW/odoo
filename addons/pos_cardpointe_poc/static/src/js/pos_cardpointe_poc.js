odoo.define('pos_cardpointe_poc.payment', function (require) {
    'use strict';

    const core = require('web.core');
    const rpc = require('web.rpc');
    const PaymentInterface = require('point_of_sale.PaymentInterface');
    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');

    const _t = core._t;

    const CardPointePOC = PaymentInterface.extend({
        send_payment_request: async function (cid) {
            this._super.apply(this, arguments);
            const order = this.pos.get_order();
            const line = order.paymentlines.find((paymentLine) => paymentLine.cid === cid);
            if (!line) {
                return false;
            }
            if (line.amount <= 0) {
                this._showError(_t('Amount must be greater than zero.'));
                line.set_payment_status('retry');
                return false;
            }

            line.set_payment_status('waitingCard');
            let result;
            try {
                result = await rpc.query({
                    route: '/pos_cardpointe_poc/start',
                    params: {
                        pos_config_id: this.pos.config.id,
                        payment_method_id: line.payment_method.id,
                        amount: line.amount,
                        currency: this.pos.currency.name,
                        order_uid: order.uid,
                        payment_line_uuid: line.cid,
                    },
                }, { shadow: true, timeout: 150000 });
            } catch (_error) {
                this._showError(_t('Could not reach Odoo server during terminal payment.'));
                line.set_payment_status('retry');
                return false;
            }

            if (result.status === 'approved') {
                const approvedAmount = this._normalizeAmount(result.amount, line.amount);
                line.set_amount(approvedAmount);
                line.cardpointe_retref = result.retref || '';
                line.cardpointe_authcode = result.authcode || '';
                line.cardpointe_respcode = result.respcode || '';
                line.cardpointe_resptext = result.resptext || '';
                line.cardpointe_token = result.token || '';
                line.cardpointe_status = 'approved';
                line.transaction_id = result.retref || '';
                line.set_payment_status('done');
                return true;
            }

            line.cardpointe_status = result.status || 'error';
            line.cardpointe_respcode = result.respcode || '';
            line.cardpointe_resptext = result.resptext || '';
            line.set_payment_status('retry');

            if (result.status === 'merchant_mode') {
                this._showError(_t('Terminal is in Merchant Mode. Open the CardPointe Integrated/Bolt app or switch terminal to Integrated mode.'));
            } else if (result.status === 'cancelled') {
                this._showError(_t('Payment cancelled on terminal.'));
            } else if (result.status === 'timeout') {
                this._showError(_t('Terminal request timed out. Please check device status and try again.'));
            } else if (result.status === 'in_use') {
                this._showError(_t('Terminal is already in use. Wait for the current transaction to finish, then try again.'));
            } else {
                this._showError(result.message || _t('Card payment not approved.'));
            }
            return false;
        },

        _normalizeAmount: function (amount, fallback) {
            if (amount === undefined || amount === null || amount === '') {
                return fallback;
            }
            const value = String(amount);
            if (value.indexOf('.') !== -1) {
                return parseFloat(value);
            }
            return parseFloat(value) / 100;
        },

        _showError: function (message) {
            Gui.showPopup('ErrorPopup', {
                title: _t('CardPointe POC'),
                body: message,
            });
        },
    });

    models.register_payment_method('cardpointe_poc', CardPointePOC);

    const CardPointePayment = (Payment) => class extends Payment {
        init_from_JSON(json) {
            super.init_from_JSON(json);
            this.cardpointe_retref = json.cardpointe_retref || '';
            this.cardpointe_authcode = json.cardpointe_authcode || '';
            this.cardpointe_respcode = json.cardpointe_respcode || '';
            this.cardpointe_resptext = json.cardpointe_resptext || '';
            this.cardpointe_token = json.cardpointe_token || '';
            this.cardpointe_status = json.cardpointe_status || '';
        }

        export_as_JSON() {
            const json = super.export_as_JSON();
            json.cardpointe_retref = this.cardpointe_retref || '';
            json.cardpointe_authcode = this.cardpointe_authcode || '';
            json.cardpointe_respcode = this.cardpointe_respcode || '';
            json.cardpointe_resptext = this.cardpointe_resptext || '';
            json.cardpointe_token = this.cardpointe_token || '';
            json.cardpointe_status = this.cardpointe_status || '';
            return json;
        }
    };

    Registries.Model.extend(models.Payment, CardPointePayment);
});
