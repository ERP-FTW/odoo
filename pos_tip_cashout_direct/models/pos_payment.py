from odoo import api, fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    tip_amount = fields.Monetary(
        string='Tip Amount',
        currency_field='currency_id',
        default=0.0,
        help='Portion of this POS payment that represents a tip.',
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list.append('tip_amount')
        return list(dict.fromkeys(fields_list))
