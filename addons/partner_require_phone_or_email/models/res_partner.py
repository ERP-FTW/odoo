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

    @api.constrains('email', 'phone', 'mobile', 'active')
    def _check_contact_method(self):
        for partner in self:
            if partner._requires_contact_method() and not partner._has_contact_method():
                raise ValidationError(
                    _('Please set at least one contact method: Email or Phone/Mobile.')
                )

    @api.constrains('email', 'phone', 'mobile', 'active')
    def _check_unique_contact_methods_cross_fields(self):
        for partner in self:
            if not partner._requires_unique_contact_methods():
                continue

            if partner.email_normalized_custom:
                dup_email = self.sudo().search([
                    ('id', '!=', partner.id),
                    ('active', '=', True),
                    ('email_normalized_custom', '=', partner.email_normalized_custom),
                ], limit=1)
                if dup_email:
                    raise ValidationError(
                        _('A contact with this email already exists: %(name)s', name=dup_email.display_name)
                    )

            for value in filter(None, [partner.phone_normalized_custom, partner.mobile_normalized_custom]):
                dup_phone = self.sudo().search([
                    ('id', '!=', partner.id),
                    ('active', '=', True),
                    '|',
                    ('phone_normalized_custom', '=', value),
                    ('mobile_normalized_custom', '=', value),
                ], limit=1)
                if dup_phone:
                    raise ValidationError(
                        _('A contact with this phone number already exists: %(name)s', name=dup_phone.display_name)
                    )

    @api.onchange('email', 'phone', 'mobile')
    def _onchange_contact_method_warning(self):
        if self and (self.email or self.phone or self.mobile) and not self._has_contact_method():
            return {
                'warning': {
                    'title': _('Missing contact method'),
                    'message': _('Email or Phone/Mobile is required.'),
                }
            }
        return {}
