# Copyright 2025
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    "name": "Latvia VAT Return (VID EDS XML export)",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Export Latvia VAT return as VID EDS XML (DokPVNv7) using report_xml",
    "author": "S3 International / OCA-friendly",
    "license": "AGPL-3",
    "depends": [
        "account_reports",
        "l10n_lv",
        "report_xml",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/vat_eds_export_wizard_views.xml",
        "report/vat_eds_xml_report.xml",
        "report/vat_eds_xml_templates.xml",
    ],
    "installable": True,
    "application": False,
}
