import re

from odoo import fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    phone_raw = fields.Char(string='Phone Raw')
    phone_extension = fields.Char(string='Phone Extension')

    def action_save_phone_raw(self):
        self.ensure_one()

        digits = re.sub(r'\D+', '', self.phone_raw or '')
        if not digits:
            raise UserError('Enter a phone number first.')

        if len(digits) == 10:
            national = digits
        elif len(digits) == 11:
            if digits[0] != '1':
                raise UserError('11-digit phone numbers must start with country code 1.')
            national = digits[1:]
        else:
            raise UserError('Phone must be 10 or 11 digits.')

        area = national[0:3]
        mid = national[3:6]
        last = national[6:10]
        formatted = f'({area}) {mid}-{last}'

        extension_digits = re.sub(r'\D+', '', self.phone_extension or '')

        self.write({
            'phone': formatted,
            'phone_raw': national,
            'phone_extension': extension_digits or False,
        })
