# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError
import requests
import json

import logging


_logger = logging.getLogger(__name__)


class PosOrderInherit(models.Model):
    _inherit = "pos.order"

    def _get_fields_for_payment_lines(self):
        payment_fields = super()._get_fields_for_payment_lines()
        return payment_fields + [
            'is_crypto_payment',
            'cryptopay_invoice_id',
            'cryptopay_payment_type',
            'cryptopay_payment_link',
            'cryptopay_payment_link_qr_code',
            'invoiced_crypto_amount',
            'conversion_rate',
            ]


    def _payment_fields(self, order, ui_paymentline): #super function to update payment fields
        fields = super(PosOrderInherit, self)._payment_fields(
            order, ui_paymentline)
        pay_method = self.env['pos.payment.method'].search(
            [('id', '=', int(ui_paymentline['payment_method_id']))])
        if pay_method != False: # if there is a payment method
            fields.update({
                'is_crypto_payment': ui_paymentline.get('is_crypto_payment'),
                'cryptopay_invoice_id': ui_paymentline.get('cryptopay_invoice_id'),
                'cryptopay_payment_type': ui_paymentline.get('cryptopay_payment_type'),
                'cryptopay_payment_link': ui_paymentline.get('cryptopay_payment_link'),
                'invoiced_crypto_amount': ui_paymentline.get('invoiced_crypto_amount'),
                'conversion_rate': ui_paymentline.get('conversion_rate'),
            })
        return fields

