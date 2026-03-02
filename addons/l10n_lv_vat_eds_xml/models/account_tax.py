from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    L10N_LV_EDS_DAR_VEIDS_SELECTION = [
        ("A", "A - Domestic taxable supplies"),
        ("N", "N - Domestic non-taxable supplies"),
        ("Z", "Z - Reverse charge supplies"),
        ("R4", "R4 - Triangular transaction supplies"),
        ("V", "V - VAT-exempt supplies"),
        ("T", "T - Distance sales / OSS supplies"),
        ("I", "I - Import transactions"),
        ("K", "K - Credit note / correction"),
        ("R1", "R1 - Special regime type 1"),
        ("R2", "R2 - Special regime type 2"),
        ("R3", "R3 - Special regime type 3"),
        ("R5", "R5 - Special regime type 5"),
        ("R6", "R6 - Special regime type 6"),
        ("R7", "R7 - Special regime type 7"),
        ("C", "C - Intra-EU acquisition"),
        ("M", "M - Margin scheme transaction"),
    ]

    l10n_lv_eds_section = fields.Selection([
        ("none", "None"),
        ("pvn1i", "PVN1I"),
        ("pvn1ii", "PVN1II"),
        ("pvn1iii", "PVN1III"),
        ("pvn2", "PVN2"),
    ], default="none", string="LV EDS Section")
    l10n_lv_eds_dar_veids = fields.Selection(
        selection=L10N_LV_EDS_DAR_VEIDS_SELECTION,
        string="LV EDS DarVeids",
    )
    l10n_lv_eds_dok_veids = fields.Selection(
        selection=[
            ("1", "1 - Invoice"),
            ("2", "2 - Receipt"),
            ("3", "3 - Non-cash payment document"),
            ("4", "4 - Credit note"),
            ("5", "5 - Other"),
            ("6", "6 - Customs declaration"),
        ],
        string="LV EDS DokVeids",
    )
    l10n_lv_eds_pazime = fields.Char(string="LV EDS Pazime")
    l10n_lv_eds_requires_partner_vat = fields.Boolean(string="LV EDS Requires Partner VAT")
    l10n_lv_eds_include_vat_amount = fields.Boolean(string="LV EDS Include VAT Amount", default=True)
