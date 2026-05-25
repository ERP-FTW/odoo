from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_payment_method(self):
        params = super()._loader_params_pos_payment_method()
        params['search_params']['fields'] += [
            'cardpointe_config_id',
            'cardpointe_manual_entry_enabled',
            'cardpointe_manual_entry_ecomind',
            'cardpointe_manual_entry_require_partner',
            'cardpointe_manual_entry_require_manager',
        ]
        return params
