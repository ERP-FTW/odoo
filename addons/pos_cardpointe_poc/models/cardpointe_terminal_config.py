from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from odoo.addons.pos_cardpointe_poc.services.cardpointe_terminal import CardPointeTerminalClient


class CardPointeTerminalConfig(models.Model):
    _name = 'pos.cardpointe.terminal.config'
    _description = 'POS CardPointe Terminal Config'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    base_url = fields.Char(default='https://bolt-uat.cardpointe.com/api', required=True)
    merchant_id = fields.Char(default='800000009875', required=True)
    merchant_config_id = fields.Many2one('cardpointe.merchant.config')
    auth_key = fields.Char(required=True)
    device_type = fields.Selection([('clover_flex', 'Clover Flex')], default='clover_flex', required=True)
    device_serial = fields.Char(string='HSN', help='Terminal hardware serial number (HSN).')
    request_timeout_seconds = fields.Integer(default=120, required=True)
    signature_mode = fields.Selection(
        [
            ('never', 'Never'),
            ('msr_over_threshold', 'MSR over threshold'),
            ('always', 'Always'),
        ],
        default='msr_over_threshold',
        required=True,
    )
    signature_threshold_amount = fields.Float(default=50.0, required=True)
    signature_capture_method = fields.Selection(
        [
            ('inline_authcard', 'Inline authCard'),
            ('post_readSignature', 'Post readSignature'),
        ],
        default='inline_authcard',
        required=True,
    )

    @api.onchange('merchant_config_id')
    def _onchange_merchant_config_id(self):
        if self.merchant_config_id:
            self.merchant_id = self.merchant_config_id.mid

    def action_test_connect(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Only administrators can run terminal connect tests.'))

        result = CardPointeTerminalClient(self).connect()
        message = _('Connect failed.')
        msg_type = 'warning'
        if result.get('ok'):
            message = _('Connect succeeded. Session key was returned by terminal API.')
            msg_type = 'success'
        elif result.get('message'):
            message = _('Connect failed: %s') % result.get('message')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('CardPointe Test Connect'),
                'message': message,
                'type': msg_type,
                'sticky': False,
            },
        }
