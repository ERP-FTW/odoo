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

            return this._waitForCardpointeToken(paymentOptionId).then(tokenPayload => {
                if (!tokenPayload || !tokenPayload.token) {
                    const wrapper = this._getCardpointeWrapperByProviderId(paymentOptionId);
                    const tokenizerUrl = wrapper ? (wrapper.dataset.tokenizerUrl || '') : '';
                    console.warn(
                        '[CARDPOINTE] Missing token from Hosted iFrame Tokenizer.',
                        {providerId: paymentOptionId, tokenizerUrl: tokenizerUrl}
                    );
                    this._enableButton();
                    $('body').unblock();
                    this._displayError(
                        _t("CardPointe"),
                        _t("We could not retrieve a payment token."),
                        _t("Please complete the secure card form and try again.")
                    );
                    return null;
                }

                return this._rpc({
                    route: this.txContext.transactionRoute,
                    params: this._prepareTransactionRouteParams(
                        'cardpointe',
                        paymentOptionId,
                        'direct'
                    ),
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
                });
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
            this._cardpointeTokenWaiters = {};

            window.addEventListener('message', event => {
                const data = this._normalizeCardpointeMessage(event);
                if (!data) {
                    return;
                }

                this._applyCardpointeIframeUpdate(data.providerId, data.payload);

                const providerId = data.providerId;
                if (!providerId) {
                    return;
                }

                const tokenPayload = this._extractCardpointeToken(data.payload);
                if (!tokenPayload) {
                    return;
                }

                this._cardpointeTokens[providerId] = tokenPayload;
                if (this._cardpointeTokenWaiters[providerId]) {
                    this._cardpointeTokenWaiters[providerId](tokenPayload);
                    delete this._cardpointeTokenWaiters[providerId];
                }
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
                const payload = this._parseCardpointeMessage(event.data);
                if (payload && payload.token) {
                    console.warn(
                        '[CARDPOINTE] Ignored token message from unexpected origin.',
                        {origin: event.origin}
                    );
                }
                return null;
            }
            const providerId = parseInt(wrapper.dataset.providerId, 10);
            if (!providerId) {
                return null;
            }

            const payload = this._parseCardpointeMessage(event.data);
            if (!payload) {
                return null;
            }
            if (!this._isCardpointeTokenMessage(payload)) {
                return {
                    providerId: providerId,
                    payload: payload,
                };
            }
            if (!payload.token) {
                console.warn(
                    '[CARDPOINTE] Tokenizer message missing token.',
                    {
                        origin: event.origin,
                        keys: this._summarizeCardpointePayloadKeys(payload),
                    }
                );
            }
            return {
                providerId: providerId,
                payload: payload,
            };
        },

        /**
         * Detect tokenization payloads, while allowing non-token iframe events.
         *
         * @private
         * @param {object} payload
         * @return {boolean}
         */
        _isCardpointeTokenMessage: function (payload) {
            return !!(
                payload && (
                    Object.prototype.hasOwnProperty.call(payload, 'token')
                    || (payload.data && Object.prototype.hasOwnProperty.call(payload.data, 'token'))
                    || (payload.response && Object.prototype.hasOwnProperty.call(payload.response, 'token'))
                    || (payload.message && typeof payload.message === 'object'
                        && Object.prototype.hasOwnProperty.call(payload.message, 'token'))
                )
            );
        },

        /**
         * Apply iframe UI updates emitted by the CardPointe tokenizer.
         *
         * @private
         * @param {number} providerId
         * @param {object} payload
         */
        _applyCardpointeIframeUpdate: function (providerId, payload) {
            const iframeHeight = this._extractCardpointeIframeHeight(payload);
            if (!iframeHeight) {
                return;
            }

            const wrapper = this._getCardpointeWrapperByProviderId(providerId);
            const iframe = wrapper ? wrapper.querySelector('iframe.o_cardpointe_iframe') : null;
            if (!iframe) {
                return;
            }
            iframe.style.height = `${iframeHeight}px`;
            iframe.style.minHeight = `${iframeHeight}px`;
        },

        /**
         * Extract iframe height updates from tokenizer postMessage payloads.
         *
         * @private
         * @param {object} payload
         * @return {number|null}
         */
        _extractCardpointeIframeHeight: function (payload) {
            if (!payload || typeof payload !== 'object') {
                return null;
            }

            const candidates = [
                payload.height,
                payload.iframeHeight,
                payload.frameHeight,
                payload.data && payload.data.height,
                payload.data && payload.data.iframeHeight,
                payload.response && payload.response.height,
                payload.response && payload.response.iframeHeight,
                payload.message && typeof payload.message === 'object' && payload.message.height,
            ];

            for (const candidate of candidates) {
                const value = this._normalizeCardpointeDimension(candidate);
                if (value) {
                    return value;
                }
            }
            return null;
        },

        /**
         * Normalize a dimension value to a valid pixel integer.
         *
         * @private
         * @param {number|string|boolean|null} value
         * @return {number|null}
         */
        _normalizeCardpointeDimension: function (value) {
            if (value === null || value === undefined || value === false) {
                return null;
            }
            const raw = typeof value === 'string' ? value.replace(/px$/i, '').trim() : value;
            const parsed = parseInt(raw, 10);
            if (!Number.isFinite(parsed) || parsed <= 0) {
                return null;
            }
            return parsed;
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
            const token = payload.token
                || (payload.data && payload.data.token)
                || (payload.response && payload.response.token)
                || (payload.message && payload.message.token);
            if (!token) {
                console.warn(
                    '[CARDPOINTE] Tokenizer payload missing token.',
                    {keys: this._summarizeCardpointePayloadKeys(payload)}
                );
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
         * Wait briefly for a CardPointe token payload.
         *
         * @private
         * @param {number} providerId
         * @return {Promise<object|null>}
         */
        _waitForCardpointeToken: function (providerId) {
            const existing = this._getCardpointeTokenPayload(providerId);
            if (existing) {
                return Promise.resolve(existing);
            }
            return new Promise(resolve => {
                this._cardpointeTokenWaiters[providerId] = resolve;
                window.setTimeout(() => {
                    if (this._cardpointeTokenWaiters[providerId]) {
                        delete this._cardpointeTokenWaiters[providerId];
                        resolve(null);
                    }
                }, 5000);
            });
        },

        /**
         * Find the CardPointe iframe wrapper by provider id.
         *
         * @private
         * @param {number} providerId
         * @return {HTMLElement|null}
         */
        _getCardpointeWrapperByProviderId: function (providerId) {
            const wrappers = document.querySelectorAll('.o_cardpointe_iframe_wrapper');
            for (const wrapper of wrappers) {
                const wrapperProviderId = parseInt(wrapper.dataset.providerId, 10);
                if (wrapperProviderId === providerId) {
                    return wrapper;
                }
            }
            return null;
        },

        /**
         * Parse a CardPointe postMessage payload.
         *
         * @private
         * @param {object|string} payload
         * @return {object|null}
         */
        _parseCardpointeMessage: function (payload) {
            if (typeof payload === 'string') {
                try {
                    return JSON.parse(payload);
                } catch (err) {
                    return null;
                }
            }
            if (payload && typeof payload === 'object') {
                return payload;
            }
            return null;
        },

        /**
         * Summarize payload keys recursively (safe for logging).
         *
         * @private
         * @param {object} payload
         * @param {number} depth
         * @return {object}
         */
        _summarizeCardpointePayloadKeys: function (payload, depth = 2) {
            if (!payload || typeof payload !== 'object' || depth < 0) {
                return {};
            }
            const summary = {};
            Object.keys(payload).forEach(key => {
                const value = payload[key];
                if (value && typeof value === 'object') {
                    summary[key] = this._summarizeCardpointePayloadKeys(value, depth - 1);
                } else {
                    summary[key] = true;
                }
            });
            return summary;
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
