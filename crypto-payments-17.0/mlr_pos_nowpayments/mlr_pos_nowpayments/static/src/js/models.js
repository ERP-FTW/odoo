odoo.define('pos_cryptopayment.models', function (require) {
var models = require('point_of_sale.models');
var PaymentCryptoPayment = require('pos_cryptopayment.payment');

models.register_payment_method('now', PaymentCryptoPayment);
});
