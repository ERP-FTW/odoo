from odoo import _, api, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _has_contact_method(self):
        """Return whether at least one usable contact method is set."""
        self.ensure_one()
        values = [self.email, self.phone, self.mobile]
        return any(bool((value or '').strip()) for value in values)

    def _requires_contact_method(self):
        """Return whether this partner should be checked by the constraint."""
        self.ensure_one()
        if not self.active:
            return False
        if self == self.env.company.partner_id:
            return False
        if self.user_ids:
            return False
        return True

    @api.constrains('email', 'phone', 'mobile', 'active')
    def _check_contact_method(self):
        for partner in self:
            if partner._requires_contact_method() and not partner._has_contact_method():
                raise ValidationError(
                    _('Please set at least one contact method: Email or Phone/Mobile.')
                )

    @api.onchange('email', 'phone', 'mobile')
    def _onchange_contact_method_warning(self):
        if self and not self._has_contact_method():
            return {
                'warning': {
                    'title': _('Missing contact method'),
                    'message': _('Email or Phone/Mobile is required.'),
                }
            }
        return {}
