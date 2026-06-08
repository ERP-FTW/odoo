from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    outbound_payment_provider_id = fields.Many2one(
        'payment.provider',
        string='Outbound Payment Provider',
        help='Provider used for outbound vendor payment execution.',
    )
