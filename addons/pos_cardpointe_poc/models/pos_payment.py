from odoo import fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    cardpointe_retref = fields.Char()
    cardpointe_authcode = fields.Char()
    cardpointe_status = fields.Char()
