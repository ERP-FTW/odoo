from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class L10nLvVatEdsExportWizard(models.TransientModel):
    _name = "l10n_lv.vat.eds.export.wizard"
    _description = "Latvia VAT Return (VID EDS) XML Export"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.today())
    is_correction = fields.Boolean(string="Correction (Precizejums)", default=False)
    phone = fields.Char(string="Phone", related="company_id.phone", readonly=False)
    email = fields.Char(string="Email", related="company_id.email", readonly=False)

    def action_export_xml(self):
        self.ensure_one()
        _logger.info(
            "LV VAT EDS XML export requested: company=%s (%s) date_from=%s date_to=%s correction=%s",
            self.company_id.display_name, self.company_id.id, self.date_from, self.date_to, self.is_correction
        )
        return self.env.ref("l10n_lv_vat_eds_xml.action_report_lv_vat_eds_xml").report_action(self)

    # -----------------------
    # Report helper methods
    # -----------------------
    def _get_vid_taxpayer_code(self):
        """VID expects registration code without 'LV' prefix in most contexts."""
        self.ensure_one()
        vat = (self.company_id.vat or "").strip()
        if vat.upper().startswith("LV"):
            vat = vat[2:]
        return vat

    def _get_period_year_month(self):
        self.ensure_one()
        # VID period is typically the month being reported; take date_to as anchor.
        dt = self.date_to or fields.Date.today()
        return dt.year, dt.month

    def _get_vat_report(self):
        """Return the Odoo VAT report definition shipped by l10n_lv."""
        self.ensure_one()
        try:
            return self.env.ref("l10n_lv.l10n_lv_vat_main_tax_report")
        except Exception:
            _logger.exception("Cannot locate VAT report xmlid l10n_lv.l10n_lv_vat_main_tax_report")
            return None

    def _build_report_options(self, report):
        self.ensure_one()
        # Robust across minor API changes: build options then override date + companies.
        options = {}
        try:
            options = report._get_options()
        except TypeError:
            # Some versions accept previous_options; try empty dict.
            options = report._get_options({})
        except Exception:
            _logger.exception("Failed to build base options for account.report %s", report)
            options = {}

        # Date range
        options.setdefault("date", {})
        options["date"].update({
            "date_from": self.date_from and str(self.date_from) or False,
            "date_to": self.date_to and str(self.date_to) or False,
            "mode": "range",
        })

        # Force company
        # Some report code uses company_ids, some uses multi_company; set both defensively.
        options["company_ids"] = [self.company_id.id]
        options.setdefault("multi_company", {})
        options["multi_company"]["company_ids"] = [self.company_id.id]

        return options

    def _get_vat_amounts_by_row_number(self):
        """Compute VAT report lines and return {row_number: amount}.

        row_number is a string like '41', '411', etc.
        """
        self.ensure_one()
        report = self._get_vat_report()
        if not report:
            return {}

        options = self._build_report_options(report)
        _logger.debug("LV VAT report options: %s", options)

        try:
            lines = report._get_lines(options)
        except Exception:
            _logger.exception("Failed to compute LV VAT report lines for options=%s", options)
            return {}

        amounts = {}
        for line in lines or []:
            code = line.get("code") or ""
            if not code.startswith("LV_"):
                continue
            row = code.replace("LV_", "")
            # 'balance' is typically the 2nd column, but we search for a column key defensively.
            amount = 0.0
            cols = line.get("columns") or []
            if cols:
                # Try common keys in order
                col = cols[-1]
                for key in ("no_format", "value", "name"):
                    if key in col:
                        amount = col.get(key)
                        break
                # If we ended up with a string formatted value, try to coerce
                if isinstance(amount, str):
                    try:
                        amount = float(amount.replace(" ", "").replace(",", "."))
                    except Exception:
                        _logger.debug("Could not coerce amount for row %s from %r", row, amount)
                        amount = 0.0

            amounts[row] = amount or 0.0

        # Minimal troubleshooting visibility
        _logger.info(
            "Computed LV VAT rows (%s): %s",
            len(amounts),
            ", ".join([f"{k}={v}" for k, v in sorted(amounts.items(), key=lambda kv: (len(kv[0]), kv[0]))][:20]) +
            (" ..." if len(amounts) > 20 else "")
        )
        return amounts

    def _get_amount(self, row_number):
        """QWeb helper: return amount for a given row (string/int)."""
        self.ensure_one()
        row = str(row_number)
        cache_key = "_lv_vat_eds_amounts_cache"
        if cache_key not in self.env.context:
            amounts = self._get_vat_amounts_by_row_number()
            # store in context for template calls
            self = self.with_context(**{cache_key: amounts})
        amounts = self.env.context.get(cache_key, {}) or {}
        return amounts.get(row, 0.0)

    def _xml_amount(self, value):
        """VID XML values are numeric; keep plain decimal with 2 dp by convention."""
        try:
            return f"{float(value):.2f}"
        except Exception:
            return "0.00"
