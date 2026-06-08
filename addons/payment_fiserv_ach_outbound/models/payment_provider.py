from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('fiserv_ach_outbound', 'Fiserv ACH Outbound')], ondelete={'fiserv_ach_outbound': 'set default'})
    fiserv_ach_enabled = fields.Boolean()
    fiserv_ach_base_url = fields.Char()
    fiserv_ach_merchid = fields.Char()
    fiserv_ach_username = fields.Char()
    fiserv_ach_password = fields.Char()
    fiserv_ach_auth_token = fields.Char(help='If integration uses an auth token from CardPointe config.')
    fiserv_ach_default_currency_id = fields.Many2one('res.currency')
    fiserv_ach_default_entry_code = fields.Selection([('CCD', 'CCD'), ('PPD', 'PPD'), ('TEL', 'TEL'), ('WEB', 'WEB')], default='CCD')
    fiserv_ach_default_description = fields.Char(default='PAYMENT')
    fiserv_ach_default_ecomind = fields.Selection([('T', 'Telephone/Mail'), ('R', 'Recurring'), ('E', 'E-commerce')])
    fiserv_ach_use_profile_tokens = fields.Boolean(default=True)

    def _fiserv_find_related_cardpointe_provider(self):
        self.ensure_one()
        return self.search([('id', '!=', self.id), ('code', 'in', ['cardpointe', 'fiserv']), ('company_id', '=', self.company_id.id)], limit=1)

    def _fiserv_get_effective_base_url(self):
        self.ensure_one()
        related = self._fiserv_find_related_cardpointe_provider()
        return self.fiserv_ach_base_url or getattr(related, 'cardpointe_base_url', False) or getattr(related, 'fiserv_ach_base_url', False)

    def _fiserv_get_effective_credentials(self):
        self.ensure_one()
        related = self._fiserv_find_related_cardpointe_provider()
        return {
            'merchid': self.fiserv_ach_merchid or getattr(related, 'cardpointe_merchid', False),
            'username': self.fiserv_ach_username or getattr(related, 'cardpointe_username', False),
            'password': self.fiserv_ach_password or getattr(related, 'cardpointe_password', False),
            'auth_token': self.fiserv_ach_auth_token or getattr(related, 'cardpointe_auth_token', False),
        }
