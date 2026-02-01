odoo.define('payment_cardpointe.payment_form', require => {
    'use strict';

    const core = require('web.core');

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const _t = core._t;

    const cardpointeMixin = {
        /**
         * Prepare the inline form of CardPointe for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the selected payment option's provider
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: function (code, paymentOptionId, flow) {
            if (code !== 'cardpointe') {
                return this._super(...arguments);
            }
            if (flow === 'token') {
                return Promise.resolve();
            }

            this._setPaymentFlow('direct');
            this._ensureCardpointeListener();
            return Promise.resolve();
        },

        /**
         * Process the CardPointe payment by exchanging the hosted token.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the selected payment option's provider
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _processPayment: function (code, paymentOptionId, flow) {
            if (code !== 'cardpointe' || flow === 'token') {
                return this._super(...arguments);
            }

            const tokenPayload = this._getCardpointeTokenPayload(paymentOptionId);
            if (!tokenPayload || !tokenPayload.token) {
                this._enableButton();
                $('body').unblock();
                this._displayError(
                    _t("CardPointe"),
                    _t("We could not retrieve a payment token."),
                    _t("Please complete the secure card form and try again.")
                );
                return Promise.resolve();
            }

            return this._rpc({
                route: this.txContext.transactionRoute,
                params: this._prepareTransactionRouteParams('cardpointe', paymentOptionId, 'direct'),
            }).then(processingValues => {
                return this._rpc({
                    route: '/payment/cardpointe/process',
                    params: {
                        'reference': processingValues.reference,
                        'partner_id': processingValues.partner_id,
                        'token': tokenPayload.token,
                        'meta': tokenPayload.meta || {},
                        'access_token': this.txContext.accessToken,
                    }
                });
            }).then(result => {
                if (!result || !result.success) {
                    this._enableButton();
                    $('body').unblock();
                    this._displayError(
                        _t("CardPointe"),
                        _t("We are not able to process your payment."),
                        _t("Please try again or use another payment method.")
                    );
                    return;
                }
                window.location = result.redirect_url || '/payment/status';
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.message.data.message
                );
            });
        },

        /**
         * Store the most recent CardPointe tokenization result.
         *
         * @private
         */
        _ensureCardpointeListener: function () {
            if (this._cardpointeListenerAttached) {
                return;
            }
            this._cardpointeListenerAttached = true;
            this._cardpointeTokens = {};

            window.addEventListener('message', event => {
                const data = this._normalizeCardpointeMessage(event);
                if (!data) {
                    return;
                }
                const providerId = data.providerId;
                if (!providerId) {
                    return;
                }

                const tokenPayload = this._extractCardpointeToken(data.payload);
                if (!tokenPayload) {
                    return;
                }

                this._cardpointeTokens[providerId] = tokenPayload;
            });
        },

        /**
         * Normalize the CardPointe postMessage payload.
         *
         * Docs: https://developer.fiserv.com/product/CardPointe/docs/?path=docs/documentation/HostediFrameTokenizer.md
         * Never log/store PAN/CVV; tokens only.
         *
         * @private
         * @param {MessageEvent} event
         * @return {object|null}
         */
        _normalizeCardpointeMessage: function (event) {
            const wrapper = this._getCardpointeWrapperByOrigin(event.origin);
            if (!wrapper) {
                return null;
            }
            const providerId = parseInt(wrapper.dataset.providerId, 10);
            if (!providerId) {
                return null;
            }

            let payload = event.data;
            if (typeof payload === 'string') {
                try {
                    payload = JSON.parse(payload);
                } catch (err) {
                    return null;
                }
            }
            return {
                providerId: providerId,
                payload: payload,
            };
        },

        /**
         * Extract the token and optional metadata from the tokenization payload.
         *
         * Docs: https://developer.fiserv.com/product/CardPointe/docs/?path=docs/documentation/HostediFrameTokenizer.md
         * Never log/store PAN/CVV; tokens only.
         *
         * @private
         * @param {object} payload
         * @return {object|null}
         */
        _extractCardpointeToken: function (payload) {
            if (!payload || typeof payload !== 'object') {
                return null;
            }
            const token = payload.token;
            if (!token) {
                return null;
            }
            return {
                token: token,
                meta: {
                    expiry_month: payload.expiry_month,
                    expiry_year: payload.expiry_year,
                    brand: payload.brand,
                    last4: payload.last4,
                },
            };
        },

        /**
         * Return the stored token payload for a provider.
         *
         * @private
         * @param {number} providerId
         * @return {object|null}
         */
        _getCardpointeTokenPayload: function (providerId) {
            return this._cardpointeTokens && this._cardpointeTokens[providerId];
        },

        /**
         * Find the CardPointe iframe wrapper that matches the postMessage origin.
         *
         * @private
         * @param {string} origin
         * @return {HTMLElement|null}
         */
        _getCardpointeWrapperByOrigin: function (origin) {
            const wrappers = document.querySelectorAll('.o_cardpointe_iframe_wrapper');
            for (const wrapper of wrappers) {
                const tokenizerUrl = wrapper.dataset.tokenizerUrl || '';
                if (!tokenizerUrl) {
                    continue;
                }
                let allowedOrigin = '';
                try {
                    allowedOrigin = new URL(tokenizerUrl).origin;
                } catch (err) {
                    continue;
                }
                if (allowedOrigin === origin) {
                    return wrapper;
                }
            }
            return null;
        },
    };

    checkoutForm.include(cardpointeMixin);
    manageForm.include(cardpointeMixin);
});
