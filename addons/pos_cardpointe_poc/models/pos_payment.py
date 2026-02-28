from odoo import fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    cardpointe_retref = fields.Char()
    cardpointe_authcode = fields.Char()
    cardpointe_respcode = fields.Char()
    cardpointe_resptext = fields.Char()
    cardpointe_token = fields.Char()
    cardpointe_status = fields.Char()
