from odoo import fields, models


class CardPointeTerminalConfig(models.Model):
    _name = 'pos.cardpointe.terminal.config'
    _description = 'POS CardPointe Terminal Config'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    base_url = fields.Char(default='https://bolt-terminal-uat.cardpointe.com', required=True)
    port = fields.Integer(default=443, required=True)
    merchant_id = fields.Char(default='800000009875', required=True)
    device_type = fields.Selection([('clover_flex', 'Clover Flex')], default='clover_flex', required=True)
    device_serial = fields.Char()
    timeout_seconds = fields.Integer(default=60, required=True)
