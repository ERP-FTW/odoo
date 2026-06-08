from odoo import fields, models


class OutboundPaymentEventLog(models.Model):
    _name = 'outbound.payment.event.log'
    _description = 'Outbound Payment Event Log'
    _order = 'create_date desc, id desc'

    transaction_id = fields.Many2one('payment.transaction', required=True, ondelete='cascade', index=True)
    payment_id = fields.Many2one('account.payment', index=True)
    direction = fields.Selection(
        [('request', 'Request'), ('response', 'Response'), ('poll', 'Poll'), ('manual', 'Manual'), ('error', 'Error')],
        required=True,
    )
    note = fields.Char()
    payload = fields.Text()
