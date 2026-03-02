from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    L10N_LV_EDS_DOK_VEIDS_SELECTION = [
        ("1", "1 - Invoice"),
        ("2", "2 - Receipt"),
        ("3", "3 - Non-cash payment document"),
        ("4", "4 - Credit note"),
        ("5", "5 - Other"),
        ("6", "6 - Customs declaration"),
    ]

    l10n_lv_eds_dok_veids = fields.Selection(
        selection=L10N_LV_EDS_DOK_VEIDS_SELECTION,
        string="LV EDS DokVeids",
        tracking=True,
    )

    def _get_default_eds_dok_veids(self):
        self.ensure_one()
        if self.move_type in ("out_refund", "in_refund"):
            return "4"
        if self.move_type in ("out_invoice", "in_invoice"):
            return "1"
        return False

    def _get_single_tax_default_eds_dok_veids(self):
        self.ensure_one()
        taxes = self.invoice_line_ids.tax_ids.filtered(lambda tax: tax.l10n_lv_eds_dok_veids)
        distinct_defaults = sorted(set(taxes.mapped("l10n_lv_eds_dok_veids")))
        return distinct_defaults[0] if len(distinct_defaults) == 1 else False

    def _ensure_eds_dok_veids_default(self):
        for move in self:
            if move.l10n_lv_eds_dok_veids:
                continue
            move.l10n_lv_eds_dok_veids = move._get_default_eds_dok_veids() or move._get_single_tax_default_eds_dok_veids()


    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._ensure_eds_dok_veids_default()
        return moves

    @api.onchange("move_type", "invoice_line_ids", "invoice_line_ids.tax_ids")
    def _onchange_ensure_eds_dok_veids_default(self):
        self._ensure_eds_dok_veids_default()
