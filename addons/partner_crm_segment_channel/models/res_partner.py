from odoo import fields, models

from .selection_values import CHANNEL_SELECTION, SEGMENT_SELECTION


class ResPartner(models.Model):
    _inherit = 'res.partner'

    segment = fields.Selection(
        selection=SEGMENT_SELECTION,
        string='Core Segment',
        index=True,
    )
    channel = fields.Selection(
        selection=CHANNEL_SELECTION,
        string='Sales Channel',
        index=True,
    )
