import logging
import re
from collections import Counter, defaultdict

from odoo import fields, models

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
    debug_logging = fields.Boolean(string="Debug Logging")
    debug_summary = fields.Text(string="Debug Summary", readonly=True)

    def action_export_xml(self):
        self.ensure_one()
        _logger.info(
            "LV VAT EDS XML export requested: company=%s (%s) date_from=%s date_to=%s correction=%s debug=%s",
            self.company_id.display_name,
            self.company_id.id,
            self.date_from,
            self.date_to,
            self.is_correction,
            self.debug_logging,
        )

        amounts = self._get_vat_amounts_by_row_number()
        annex_data = self._get_annex_data()
        self.debug_summary = self._build_debug_summary(amounts, annex_data)

        return self.env.ref("l10n_lv_vat_eds_xml.action_report_lv_vat_eds_xml").report_action(self)

    def _build_debug_summary(self, amounts, annex_data):
        self.ensure_one()
        target_rows = self._get_target_vat_row_numbers()
        available_rows = sorted(amounts.keys(), key=lambda row: (len(row), row))
        missing_rows = [row for row in target_rows if row not in amounts]
        sections = annex_data.get("sections", {})
        counters = annex_data.get("counters", Counter())

        return "\n".join([
            f"company={self.company_id.display_name} ({self.company_id.id})",
            f"period={self.date_from}..{self.date_to}",
            f"vat_rows_available={','.join(available_rows)}",
            f"vat_rows_missing={','.join(missing_rows)}",
            "annex_rows=" + ",".join(f"{section}:{len(rows)}" for section, rows in sections.items()),
            "annex_counters=" + ",".join(f"{key}:{value}" for key, value in sorted(counters.items())),
        ])

    # -----------------------
    # XML helper methods
    # -----------------------
    def _xml_bool(self, value):
        return "true" if bool(value) else "false"

    def _xml_date(self, value):
        return value and fields.Date.to_string(value) or None

    def _xml_nil_attr(self):
        return {"xsi:nil": "true"}

    def _should_nil(self, value):
        return value is None or value is False or value == ""

    def _xml_text(self, value):
        if value in (None, False):
            return ""
        text = str(value).strip()
        return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)

    def _xml_amount(self, value):
        try:
            return f"{float(value):.2f}"
        except Exception:
            return "0.00"

    # -----------------------
    # Header helper methods
    # -----------------------
    def _get_vid_taxpayer_code(self):
        self.ensure_one()
        vat = (self.company_id.vat or "").strip()
        if vat.upper().startswith("LV"):
            vat = vat[2:]
        return vat

    def _get_period_year_month(self):
        self.ensure_one()
        dt = self.date_to or fields.Date.today()
        return dt.year, dt.month

    def _get_preparer_name(self):
        self.ensure_one()
        return self._xml_text(self.env.user.name)

    def _get_iban(self):
        self.ensure_one()
        bank = self.company_id.partner_id.bank_ids[:1]
        return self._xml_text(bank.acc_number) if bank else None

    # -----------------------
    # VAT totals (account.report driven)
    # -----------------------
    def _get_target_vat_row_numbers(self):
        return [
            "40", "41", "411", "42", "421", "43", "44", "45", "451", "46", "47", "48", "481", "482",
            "49", "50", "51", "511", "52", "521", "53", "54", "55", "56", "57", "58", "59", "60",
            "61", "62", "63", "64", "65", "66", "67",
        ]

    def _get_vat_report(self):
        self.ensure_one()
        try:
            return self.env.ref("l10n_lv.l10n_lv_vat_main_tax_report")
        except Exception:
            _logger.exception("Cannot locate VAT report xmlid l10n_lv.l10n_lv_vat_main_tax_report")
            return None

    def _build_report_options(self, report):
        self.ensure_one()
        options = {}
        report_company = report.with_company(self.company_id)
        try:
            get_options = getattr(report_company, "get_options", None)
            if get_options:
                options = get_options(previous_options={})
            else:
                # Compatibility with older account.report APIs.
                options = report_company._get_options({})
        except Exception:
            _logger.exception("Failed to build base options for account.report %s", report)
            options = {"report_id": report_company.id}

        options.setdefault("date", {})
        options["date"].update({
            "date_from": self.date_from and str(self.date_from) or False,
            "date_to": self.date_to and str(self.date_to) or False,
            "mode": "range",
        })
        options["company_ids"] = [self.company_id.id]
        options.setdefault("multi_company", {})
        options["multi_company"]["company_ids"] = [self.company_id.id]
        options["report_id"] = report_company.id
        return options

    def _get_balance_column_index(self, options, lines):
        for idx, column in enumerate((options or {}).get("columns") or []):
            if column.get("expression_label") == "balance":
                return idx
        for line in lines or []:
            for idx, col in enumerate(line.get("columns") or []):
                if col.get("expression_label") == "balance":
                    return idx
        return -1

    def _extract_amount_from_line(self, line, balance_index):
        columns = line.get("columns") or []
        column = columns[balance_index] if (balance_index >= 0 and balance_index < len(columns)) else (columns[-1] if columns else {})
        raw_amount = column.get("no_format")
        if raw_amount is None:
            raw_amount = column.get("value")
        if raw_amount is None:
            raw_amount = column.get("name")
        if isinstance(raw_amount, str):
            try:
                raw_amount = float(raw_amount.replace(" ", "").replace(",", "."))
            except Exception:
                raw_amount = 0.0
        return raw_amount or 0.0

    def _get_vat_amounts_by_row_number(self):
        self.ensure_one()
        report = self._get_vat_report()
        if not report:
            return {}

        report = report.with_company(self.company_id)
        options = self._build_report_options(report)
        if self.debug_logging:
            _logger.info("LV VAT report options for XML export: %s", options)

        try:
            lines = report._get_lines(options)
        except Exception:
            _logger.exception("Failed to compute LV VAT report lines for options=%s", options)
            return {}

        balance_idx = self._get_balance_column_index(options, lines)
        amounts = {}
        for line in lines or []:
            code = line.get("code") or ""
            if not code.startswith("LV_"):
                continue
            row_number = code.replace("LV_", "")
            amounts[row_number] = self._extract_amount_from_line(line, balance_idx)

        target_rows = self._get_target_vat_row_numbers()
        missing_rows = [row for row in target_rows if row not in amounts]
        extra_rows = [row for row in amounts if row not in target_rows]
        _logger.info(
            "LV VAT XML mapping complete. balance_col=%s rows=%s missing=%s extra=%s",
            balance_idx,
            len(amounts),
            missing_rows,
            sorted(extra_rows, key=lambda row: (len(row), row)),
        )
        if self.debug_logging:
            _logger.info(
                "LV VAT XML row map: %s",
                ", ".join(f"R{row}={self._xml_amount(amounts.get(row, 0.0))}" for row in target_rows),
            )
        return amounts

    def _get_amount(self, row_number):
        self.ensure_one()
        return self._get_vat_amounts_by_row_number().get(str(row_number), 0.0)

    # -----------------------
    # Annex framework (tax-driven)
    # -----------------------
    def _get_annex_data(self):
        self.ensure_one()
        company = self.company_id
        move_domain = [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("move_type", "in", ["out_invoice", "out_refund", "in_invoice", "in_refund"]),
        ]
        moves = self.env["account.move"].with_company(company).search(move_domain)
        line_domain = [("move_id", "in", moves.ids)]
        lines = self.env["account.move.line"].with_company(company).search(line_domain)

        taxes = self.env["account.tax"].with_company(company).search([
            ("l10n_lv_eds_section", "!=", "none"),
            "|", ("company_id", "=", company.id), ("company_id", "=", False),
        ])
        mapped_taxes = {tax.id: tax.with_company(company) for tax in taxes}

        grouped = defaultdict(lambda: {"base": 0.0, "vat": 0.0, "include_vat": True})
        counters = Counter()
        reasons = Counter()

        counters["moves_scanned"] = len(moves)
        counters["move_lines_scanned"] = len(lines)
        counters["mapped_taxes"] = len(mapped_taxes)

        for line in lines:
            if line.display_type in ("line_note", "line_section"):
                reasons["non_transaction_line"] += 1
                continue
            applied_taxes = line.tax_line_id or line.tax_ids
            if not applied_taxes:
                reasons["line_without_taxes"] += 1
                continue

            matched_taxes = applied_taxes.filtered(lambda t: t.id in mapped_taxes)
            if not matched_taxes:
                reasons["tax_unmapped_to_eds"] += 1
                continue

            move = line.move_id
            partner = move.partner_id.commercial_partner_id
            partner_vat = self._get_partner_vat(partner)
            partner_country = partner.country_id.code or ""

            for tax in matched_taxes:
                cfg_tax = mapped_taxes[tax.id]
                if not cfg_tax.l10n_lv_eds_dar_veids:
                    reasons["tax_missing_dar_veids"] += 1
                    continue
                if cfg_tax.l10n_lv_eds_requires_partner_vat and not partner_vat:
                    reasons["partner_vat_missing"] += 1
                    continue
                if not partner_country:
                    reasons["partner_country_missing"] += 1
                    continue

                section = cfg_tax.l10n_lv_eds_section
                key = (
                    section,
                    cfg_tax.l10n_lv_eds_dar_veids,
                    cfg_tax.l10n_lv_eds_dok_veids or self._default_doc_type(move),
                    cfg_tax.l10n_lv_eds_pazime or "",
                    partner_country,
                    partner_vat,
                    self._xml_text(partner.name),
                    self._xml_text(move.name or move.ref),
                    move.invoice_date or move.date,
                    move.currency_id.name if move.currency_id and move.currency_id != company.currency_id else None,
                )
                bucket = grouped[key]
                bucket["include_vat"] = bool(cfg_tax.l10n_lv_eds_include_vat_amount)
                if line.tax_line_id:
                    bucket["vat"] += abs(line.balance)
                else:
                    bucket["base"] += abs(line.balance)

        counters.update(reasons)

        section_rows = {"pvn1i": [], "pvn1ii": [], "pvn1iii": [], "pvn2": []}
        for key, values in grouped.items():
            (
                section,
                dar_veids,
                dok_veids,
                pazime,
                partner_country,
                partner_vat,
                partner_name,
                doc_number,
                doc_date,
                currency,
            ) = key
            row = {
                "dar_veids": dar_veids,
                "dok_veids": dok_veids,
                "pazime": pazime,
                "partner_country": partner_country,
                "partner_vat": partner_vat,
                "partner_name": partner_name,
                "doc_number": doc_number,
                "doc_date": self._xml_date(doc_date),
                "currency": currency,
                "base_amount": self._xml_amount(values["base"]),
                "vat_amount": self._xml_amount(values["vat"]) if values["include_vat"] else None,
            }
            section_rows.setdefault(section, []).append(row)

        for section_name, rows in section_rows.items():
            rows.sort(key=lambda row: (row["doc_date"] or "", row["doc_number"] or "", row["partner_name"] or ""))
            counters[f"rows_{section_name}"] = len(rows)

        counters["excluded_total"] = sum(reasons.values())
        if self.debug_logging:
            _logger.info("LV VAT XML annex counters: %s", dict(counters))
            _logger.info("LV VAT XML annex top excluded reasons: %s", reasons.most_common(10))

        return {
            "sections": section_rows,
            "counters": counters,
        }

    def _get_annex_rows(self, section):
        self.ensure_one()
        return self._get_annex_data().get("sections", {}).get(section, [])

    def _get_partner_vat(self, partner):
        vat = (partner.vat or "").strip()
        if vat.upper().startswith("LV"):
            vat = vat[2:]
        return vat

    def _default_doc_type(self, move):
        if move.move_type in ("out_refund", "in_refund"):
            return "K"
        return "R"
