from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_lv_eds_section = fields.Selection(
        selection=lambda self: self.env["account.tax"]._fields["l10n_lv_eds_section"].selection,
        string="LV EDS Section",
        tracking=True,
    )
    l10n_lv_eds_dar_veids = fields.Selection(
        selection=lambda self: self.env["account.tax"]._fields["l10n_lv_eds_dar_veids"].selection,
        string="LV EDS DarVeids",
        tracking=True,
    )

    def _get_primary_eds_tax(self):
        self.ensure_one()
        taxes = self.tax_ids.sorted("id")
        return taxes[:1]

    @api.onchange("tax_ids")
    def _onchange_tax_ids_set_eds_defaults(self):
        for line in self:
            primary_tax = line._get_primary_eds_tax()
            if not primary_tax:
                continue
            if not line.l10n_lv_eds_section:
                line.l10n_lv_eds_section = primary_tax.l10n_lv_eds_section
            if not line.l10n_lv_eds_dar_veids:
                line.l10n_lv_eds_dar_veids = primary_tax.l10n_lv_eds_dar_veids
