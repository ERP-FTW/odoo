odoo.define("point_of_sale.NowValidatePaymentScreen", function (require) {
    "use strict";
    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const Registries = require("point_of_sale.Registries");
    var rpc = require('web.rpc');
  
    const NowValidatePaymentScreen = (PaymentScreen) =>
      class extends PaymentScreen {
        setup() {
          super.setup();
        }
        async validateOrder(isForceValidate) {
            for (let line of this.paymentLines) {
            console.log("called now validation");
            if(line.is_crypto_payment && line.payment_method.use_payment_terminal == 'now') {
            try {
                let order_id = this.env.pos.get_order().uid;
                let api_resp = await rpc.query({
                    model: 'pos.payment.method',
                    method: 'now_check_payment_status',
                    args: [{ invoice_id: line.cryptopay_invoice_id, pm_id: line.payment_method.id, order_id: order_id }],
                }, {
                    silent: true,
                });
                console.log(api_resp);
                console.log(api_resp.payment_status);

                if (api_resp.payment_status == 'finished') {
                     console.log("valid now transaction");
                     line.invoiced_crypto_amount = api_resp.pay_amount;
                     line.cryptopay_payment_type = api_resp.pay_currency;
                     let conversion_rate = line.amount/line.invoiced_crypto_amount;
                     line.conversion_rate = conversion_rate.toFixed(2);
                     line.crypto_payment_status = 'Invoice Paid';
                     line.set_payment_status('done');
				}
                                else if (api_resp.payment_status == 'waiting' || api_resp.payment_status == 'not_found' || api_resp.payment_status == 'found') {
	                                this.showPopup("ErrorPopup", {
       		                                 title: this.env._t("Payment Request Unpaid"),
               		                         body: this.env._t("Payment Unpaid, retry after customer confirms funds have been sent. Status: " + api_resp.payment_status),
                       		        });
                                }

                                else if (api_resp.payment_status == 'confirming' || api_resp.payment_status == 'confirmed' || api_resp.payment_status == 'sending') {
	                                this.showPopup("ErrorPopup", {
       		                                 title: this.env._t("Payment Request Pending"),
               		                         body: this.env._t("Payment Pending, funds are being transferred and will be valid once confirmed. Status: " + api_resp.payment_status),
                       		        });
                                }

                                else if (api_resp.payment_status == 'partially_paid'  || api_resp.payment_status == 'refunded') {
	                                this.showPopup("ErrorPopup", {
       		                                 title: this.env._t("Payment Request Dispute"),
               		                         body: this.env._t("Payment Pending, partial payment or customer requested refund. Have manager confirm with customer. Status: " + api_resp.payment_status),
                       		        });
                                }


				else if (api_resp.payment_status == 'expired' || api_resp.payment_status == 'failed') {
						console.log("expired now transaction");
				        this.showPopup("ErrorPopup", {
                                                 title: this.env._t("Payment Request Failed"),
                                                 body: this.env._t("Payment Request failed, retry to send another send request. Status: " + api_resp.payment_status),
                                        });
				}}
				catch (error) {
                 console.log(error);
                 return false;
             }}
            }
          super.validateOrder(isForceValidate);
        }
      };
    // CustomValidatePaymentScreen.template = "point_of_sale.CustomValidatePaymentScreenTemplate";
  
    Registries.Component.extend(PaymentScreen, NowValidatePaymentScreen);
  
    return NowValidatePaymentScreen;
  });
  
