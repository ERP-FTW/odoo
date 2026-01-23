# -*- coding: utf-8 -*-

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            record._log_manual_amount_currency(vals)
        return records

    def write(self, vals):
        res = super().write(vals)
        self._log_manual_amount_currency(vals)
        return res

    def _log_manual_amount_currency(self, vals):
        if "amount_currency" not in vals:
            return
        for line in self:
            foreign_currency_id = vals.get("foreign_currency_id") or line.foreign_currency_id.id
            if not foreign_currency_id:
                _logger.warning(
                    "Bank statement line %s has a manual amount_currency without a foreign currency.",
                    line.id or "new",
                )
                continue
            _logger.info(
                "Bank statement line %s uses a manual amount_currency for currency %s.",
                line.id,
                line.foreign_currency_id.display_name,
            )
