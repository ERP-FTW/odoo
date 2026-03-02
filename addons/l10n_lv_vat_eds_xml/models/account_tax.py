from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_lv_eds_section = fields.Selection([
        ("none", "None"),
        ("pvn1i", "PVN1I"),
        ("pvn1ii", "PVN1II"),
        ("pvn1iii", "PVN1III"),
        ("pvn2", "PVN2"),
    ], default="none", string="LV EDS Section")
    l10n_lv_eds_dar_veids = fields.Char(string="LV EDS DarVeids")
    l10n_lv_eds_dok_veids = fields.Char(string="LV EDS DokVeids")
    l10n_lv_eds_pazime = fields.Char(string="LV EDS Pazime")
    l10n_lv_eds_requires_partner_vat = fields.Boolean(string="LV EDS Requires Partner VAT")
    l10n_lv_eds_include_vat_amount = fields.Boolean(string="LV EDS Include VAT Amount", default=True)