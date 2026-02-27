odoo.define('pos_cardpointe_poc.payment', function (require) {
    'use strict';

    const core = require('web.core');
    const rpc = require('web.rpc');
    const PaymentInterface = require('point_of_sale.PaymentInterface');
    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

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

            line.set_payment_status('waiting');
            let start;
            try {
                start = await rpc.query({
                    route: '/pos_cardpointe_poc/start',
                    params: {
                        pos_config_id: this.pos.config.id,
                        payment_method_id: line.payment_method.id,
                        amount: line.amount,
                        currency: this.pos.currency.name,
                        order_uid: order.uid,
                        payment_line_uuid: line.cid,
                    },
                }, {shadow: true});
            } catch (_error) {
                this._showError(_t('Could not reach Odoo server.'));
                line.set_payment_status('retry');
                return false;
            }

            if (start.status !== 'started' || !start.request_id) {
                this._showError(start.message || _t('Could not start CardPointe transaction.'));
                line.set_payment_status('retry');
                return false;
            }

            return await this._pollStatus(line, start.request_id);
        },

        _pollStatus: async function (line, requestId) {
            for (let i = 0; i < 120; i++) {
                await new Promise((resolve) => setTimeout(resolve, 1000));
                let poll;
                try {
                    poll = await rpc.query({
                        route: '/pos_cardpointe_poc/poll',
                        params: {
                            payment_method_id: line.payment_method.id,
                            request_id: requestId,
                        },
                    }, {shadow: true});
                } catch (_error) {
                    this._showError(_t('Lost connection while polling terminal status.'));
                    line.set_payment_status('retry');
                    return false;
                }

                if (poll.status === 'pending' || poll.status === 'started') {
                    continue;
                }

                if (poll.status === 'approved') {
                    line.set_amount(poll.amount || line.amount);
                    line.cardpointe_retref = poll.retref || '';
                    line.cardpointe_authcode = poll.authcode || '';
                    line.cardpointe_status = 'approved';
                    line.card_type = poll.brand || '';
                    line.transaction_id = poll.retref || '';
                    line.cardholder_name = poll.last4 ? `****${poll.last4}` : '';
                    line.set_payment_status('done');
                    return true;
                }

                line.cardpointe_status = poll.status || 'error';
                line.set_payment_status('retry');
                this._showError(poll.message || _t('Card payment not approved.'));
                return false;
            }

            line.cardpointe_status = 'timeout';
            line.set_payment_status('retry');
            this._showError(_t('Terminal timeout.'));
            return false;
        },

        _showError: function (message) {
            this.pos.chrome.showPopup('ErrorPopup', {
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
            this.cardpointe_status = json.cardpointe_status || '';
        }

        export_as_JSON() {
            const json = super.export_as_JSON();
            json.cardpointe_retref = this.cardpointe_retref || '';
            json.cardpointe_authcode = this.cardpointe_authcode || '';
            json.cardpointe_status = this.cardpointe_status || '';
            return json;
        }
    };

    Registries.Model.extend(models.Payment, CardPointePayment);
});
