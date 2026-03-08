from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    email_normalized_custom = fields.Char(
        compute='_compute_contact_norm',
        store=True,
        index=True,
    )
    phone_normalized_custom = fields.Char(
        compute='_compute_contact_norm',
        store=True,
        index=True,
    )
    mobile_normalized_custom = fields.Char(
        compute='_compute_contact_norm',
        store=True,
        index=True,
    )

    has_duplicate_email_warning = fields.Boolean(
        compute='_compute_contact_duplicate_warning',
        search='_search_has_duplicate_email_warning',
    )
    has_duplicate_phone_warning = fields.Boolean(
        compute='_compute_contact_duplicate_warning',
        search='_search_has_duplicate_phone_warning',
    )
    has_duplicate_mobile_warning = fields.Boolean(
        compute='_compute_contact_duplicate_warning',
        search='_search_has_duplicate_mobile_warning',
    )
    has_contact_duplicate_warning = fields.Boolean(
        compute='_compute_contact_duplicate_warning',
        search='_search_has_contact_duplicate_warning',
    )
    duplicate_contact_warning_message = fields.Text(
        compute='_compute_contact_duplicate_warning',
    )

    @api.model
    def _normalize_email(self, email):
        email = (email or '').strip().lower()
        return email or False

    @api.model
    def _normalize_phone(self, phone):
        phone = (phone or '').strip()
        digits = ''.join(char for char in phone if char.isdigit())
        return digits or False

    @api.depends('email', 'phone', 'mobile', 'active', 'user_ids')
    def _compute_contact_norm(self):
        for partner in self:
            if partner._requires_unique_contact_methods():
                partner.email_normalized_custom = partner._normalize_email(partner.email)
                partner.phone_normalized_custom = partner._normalize_phone(partner.phone)
                partner.mobile_normalized_custom = partner._normalize_phone(partner.mobile)
            else:
                partner.email_normalized_custom = False
                partner.phone_normalized_custom = False
                partner.mobile_normalized_custom = False

    def _has_contact_method(self):
        self.ensure_one()
        values = [self.email, self.phone, self.mobile]
        return any(bool((value or '').strip()) for value in values)

    def _requires_contact_method(self):
        self.ensure_one()
        if not self.active:
            return False
        if self == self.env.company.partner_id:
            return False
        if self.user_ids:
            return False
        return True

    def _requires_unique_contact_methods(self):
        self.ensure_one()
        return self._requires_contact_method()

    def _find_partner_duplicate_contact(self, field_name, value):
        self.ensure_one()
        if not value:
            return self.env['res.partner']
        return self.sudo().search([
            ('id', '!=', self.id),
            ('active', '=', True),
            (field_name, '=', value),
        ], limit=1)

    def _find_partner_duplicate_phone(self, value):
        self.ensure_one()
        if not value:
            return self.env['res.partner']
        return self.sudo().search([
            ('id', '!=', self.id),
            ('active', '=', True),
            '|',
            ('phone_normalized_custom', '=', value),
            ('mobile_normalized_custom', '=', value),
        ], limit=1)

    def _get_duplicate_warning_details(self, normalized_email=None, normalized_phone=None, normalized_mobile=None):
        self.ensure_one()
        duplicate_email = self._find_partner_duplicate_contact(
            'email_normalized_custom',
            normalized_email if normalized_email is not None else self.email_normalized_custom,
        )
        duplicate_phone = self._find_partner_duplicate_phone(
            normalized_phone if normalized_phone is not None else self.phone_normalized_custom,
        )
        duplicate_mobile = self._find_partner_duplicate_phone(
            normalized_mobile if normalized_mobile is not None else self.mobile_normalized_custom,
        )

        duplicate_lines = []
        if duplicate_email:
            duplicate_lines.append(
                _('Possible duplicate email with %(name)s', name=duplicate_email.display_name)
            )
        if duplicate_phone:
            duplicate_lines.append(
                _('Possible duplicate phone with %(name)s', name=duplicate_phone.display_name)
            )
        if duplicate_mobile:
            duplicate_lines.append(
                _('Possible duplicate mobile with %(name)s', name=duplicate_mobile.display_name)
            )

        return {
            'has_duplicate_email_warning': bool(duplicate_email),
            'has_duplicate_phone_warning': bool(duplicate_phone),
            'has_duplicate_mobile_warning': bool(duplicate_mobile),
            'duplicate_contact_warning_message': '\n'.join(duplicate_lines) or False,
        }

    @api.depends(
        'email_normalized_custom',
        'phone_normalized_custom',
        'mobile_normalized_custom',
        'active',
        'user_ids',
    )
    def _compute_contact_duplicate_warning(self):
        for partner in self:
            partner.has_duplicate_email_warning = False
            partner.has_duplicate_phone_warning = False
            partner.has_duplicate_mobile_warning = False
            partner.has_contact_duplicate_warning = False
            partner.duplicate_contact_warning_message = False

            if not partner._requires_unique_contact_methods():
                continue

            details = partner._get_duplicate_warning_details()
            partner.has_duplicate_email_warning = details['has_duplicate_email_warning']
            partner.has_duplicate_phone_warning = details['has_duplicate_phone_warning']
            partner.has_duplicate_mobile_warning = details['has_duplicate_mobile_warning']
            partner.has_contact_duplicate_warning = (
                partner.has_duplicate_email_warning
                or partner.has_duplicate_phone_warning
                or partner.has_duplicate_mobile_warning
            )
            partner.duplicate_contact_warning_message = details['duplicate_contact_warning_message']

    @api.model
    def _search_duplicate_warning(self, operator, value, flag_getter):
        if operator not in ('=', '!='):
            return [('id', '=', 0)]

        expect_true = (operator == '=' and value) or (operator == '!=' and not value)
        partners = self.search([('active', '=', True)])
        duplicated_ids = partners.filtered(
            lambda p: p._requires_unique_contact_methods() and flag_getter(p)
        ).ids
        return [('id', 'in' if expect_true else 'not in', duplicated_ids)]

    @api.model
    def _search_has_duplicate_email_warning(self, operator, value):
        return self._search_duplicate_warning(
            operator,
            value,
            lambda p: p._get_duplicate_warning_details()['has_duplicate_email_warning'],
        )

    @api.model
    def _search_has_duplicate_phone_warning(self, operator, value):
        return self._search_duplicate_warning(
            operator,
            value,
            lambda p: p._get_duplicate_warning_details()['has_duplicate_phone_warning'],
        )

    @api.model
    def _search_has_duplicate_mobile_warning(self, operator, value):
        return self._search_duplicate_warning(
            operator,
            value,
            lambda p: p._get_duplicate_warning_details()['has_duplicate_mobile_warning'],
        )

    @api.model
    def _search_has_contact_duplicate_warning(self, operator, value):
        return self._search_duplicate_warning(
            operator,
            value,
            lambda p: any(p._get_duplicate_warning_details()[flag] for flag in [
                'has_duplicate_email_warning',
                'has_duplicate_phone_warning',
                'has_duplicate_mobile_warning',
            ]),
        )

    @api.constrains('email', 'phone', 'mobile', 'active')
    def _check_contact_method(self):
        for partner in self:
            if partner._requires_contact_method() and not partner._has_contact_method():
                raise ValidationError(
                    _('Please set at least one contact method: Email or Phone/Mobile.')
                )

    @api.onchange('email', 'phone', 'mobile')
    def _onchange_contact_method_warning(self):
        if not self:
            return {}

        if not self._has_contact_method() and self._requires_contact_method():
            return {
                'warning': {
                    'title': _('Missing contact method'),
                    'message': _('Email or Phone/Mobile is required.'),
                }
            }

        if not self._requires_unique_contact_methods():
            return {}

        details = self._get_duplicate_warning_details(
            normalized_email=self._normalize_email(self.email),
            normalized_phone=self._normalize_phone(self.phone),
            normalized_mobile=self._normalize_phone(self.mobile),
        )
        if not any([
            details['has_duplicate_email_warning'],
            details['has_duplicate_phone_warning'],
            details['has_duplicate_mobile_warning'],
        ]):
            return {}

        message_lines = []
        if details['has_duplicate_email_warning']:
            message_lines.append(_('Possible duplicate email detected.'))
        if details['has_duplicate_phone_warning']:
            message_lines.append(_('Possible duplicate phone detected.'))
        if details['has_duplicate_mobile_warning']:
            message_lines.append(_('Possible duplicate mobile detected.'))
        if details['duplicate_contact_warning_message']:
            message_lines.append(details['duplicate_contact_warning_message'])

        return {
            'warning': {
                'title': _('Potential duplicate contact methods'),
                'message': '\n'.join(message_lines),
            }
        }
