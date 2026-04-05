import logging
import requests
import werkzeug
import time
import json
import hashlib
import hmac
import base64
from datetime import datetime, timezone

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, AccessError



_logger = logging.getLogger(__name__)
TIMEOUT = 10

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    # crypto payment 
    server_url = fields.Char(string='Server URL')
    api_key = fields.Char(string='API Key') #use account API key not store API key
    crypto_minimum_amount = fields.Float("Order minimum fiat amount for crypto payment")
    crypto_maximum_amount = fields.Float("Order maximum fiat amount for crypto payment")


    def _test_connection(self):
        return {'status_code': 200}

    def action_test_connection(self): # turns test_cryptopay_server_connection into a message for user
        response = self._test_connection()

        is_success = True if response.status_code == 200 else False
        type = (
            "success"
            if is_success
            else "danger"
        )
        messages = (
            "Everything seems properly set up!"
            if is_success
            else "Server credential is wrong. Please check credential."
        )
        title = _("Connection Testing")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": messages,
                "sticky": False,
                "type": type
            },
        }

