from odoo import fields, models


class CardPointeTerminalConfig(models.Model):
    _name = 'pos.cardpointe.terminal.config'
    _description = 'POS CardPointe Terminal Config'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    base_url = fields.Char(default='https://bolt-uat.cardpointe.com/api', required=True)
    merchant_id = fields.Char(default='800000009875', required=True)
    auth_key = fields.Char(required=True)
    device_type = fields.Selection([('clover_flex', 'Clover Flex')], default='clover_flex', required=True)
    device_serial = fields.Char(string='HSN', help='Terminal hardware serial number (HSN).')
    request_timeout_seconds = fields.Integer(default=120, required=True)
    gateway_base_url = fields.Char(
        default='https://fts-uat.cardconnect.com/cardconnect/rest/',
        required=True,
        help='CardPointe Gateway REST base URL used for inquire/void/refund.',
    )
    gateway_username = fields.Char(help='CardPointe Gateway API username (server-side only).')
    gateway_password = fields.Char(help='CardPointe Gateway API password (server-side only).')
