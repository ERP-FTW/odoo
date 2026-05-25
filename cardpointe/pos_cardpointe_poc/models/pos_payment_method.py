from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    cardpointe_config_id = fields.Many2one('pos.cardpointe.terminal.config', string='CardPointe Config')
    cardpointe_manual_entry_enabled = fields.Boolean(
        string='Enable Manual Card Entry',
        default=False,
        help='Allow POS cashiers to use CardPointe Hosted iFrame Tokenizer as a manual card entry fallback.',
    )
    cardpointe_manual_entry_ecomind = fields.Selection(
        [("E", "E - Ecommerce"), ("T", "T - Telephone/Mail")],
        string='Manual Entry ecomind',
        default='E',
        required=True,
        help='Card-not-present transaction origin indicator for POS manual entry fallback.',
    )
    cardpointe_manual_entry_require_partner = fields.Boolean(string='Require Customer for Manual Entry', default=False)
    cardpointe_manual_entry_require_manager = fields.Boolean(string='Require Manager for Manual Entry', default=False)

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('cardpointe_poc', 'CardPointe POC')]

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        super()._onchange_use_payment_terminal()
        if self.use_payment_terminal != 'cardpointe_poc':
            self.cardpointe_config_id = False
