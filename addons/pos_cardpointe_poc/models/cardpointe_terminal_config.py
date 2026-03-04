from odoo import fields, models


class CardPointeTerminalConfig(models.Model):
    _name = 'pos.cardpointe.terminal.config'
    _description = 'POS CardPointe Terminal Config'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    base_url = fields.Char(default='https://bolt-uat.cardpointe.com/api', required=True)
    merchant_config_id = fields.Many2one('cardpointe.merchant.config', required=True)
    merchant_id = fields.Char(related='merchant_config_id.mid', readonly=True)
    auth_key = fields.Char(required=True)
    device_type = fields.Selection([('clover_flex', 'Clover Flex')], default='clover_flex', required=True)
    device_serial = fields.Char(string='HSN', help='Terminal hardware serial number (HSN).')
    request_timeout_seconds = fields.Integer(default=120, required=True)
