import logging
import re

from odoo import fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    phone_raw = fields.Char(string='Phone Raw')
    phone_extension = fields.Char(string='Phone Extension')

    def action_save_phone_raw(self):
        self.ensure_one()

        digits = re.sub(r'\D+', '', self.phone_raw or '')
        _logger.info(
            "Save Phone clicked for partner id=%s, name=%s, phone_raw_input=%r, sanitized_digits=%s, length=%s",
            self.id,
            self.display_name,
            self.phone_raw,
            digits,
            len(digits),
        )

        if not digits:
            raise UserError('Enter a phone number first.')

        if len(digits) == 10:
            national = digits
        elif len(digits) == 11:
            if digits[0] != '1':
                _logger.warning(
                    "Invalid 11-digit phone for partner id=%s, sanitized_digits=%s",
                    self.id,
                    digits,
                )
                raise UserError('11-digit phone numbers must start with country code 1.')
            national = digits[1:]
        else:
            _logger.warning(
                "Invalid phone length for partner id=%s, phone_raw_input=%r, sanitized_digits=%s, length=%s",
                self.id,
                self.phone_raw,
                digits,
                len(digits),
            )
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
