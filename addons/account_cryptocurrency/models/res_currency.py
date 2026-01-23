from odoo import fields, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    is_cryptocurrency = fields.Boolean(
        string="Cryptocurrency",
        help="Enable if this currency represents a cryptocurrency.",
    )
    crypto_symbol = fields.Char(
        string="Crypto Symbol",
        help="Optional ticker or symbol used by crypto exchanges.",
    )
