from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    ach_account_type = fields.Selection([('ECHK', 'Checking'), ('ESAV', 'Savings')])
    ach_account_holder_name = fields.Char()
    ach_profile_id = fields.Char(help='Optional CardPointe profile/account identifier for ACH.')
    ach_token = fields.Char(help='Optional CardSecure token if already stored.')
    allow_outbound_ach = fields.Boolean(default=True)
    bank_aba = fields.Char(size=9, help='ACH routing number used when sending clear account number.')
