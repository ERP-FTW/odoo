from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    balance_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_balance_currency_id",
    )
    current_balance = fields.Monetary(
        string="Current Balance",
        currency_field="balance_currency_id",
        compute="_compute_current_balance",
    )

    def _compute_balance_currency_id(self):
        for journal in self:
            journal.balance_currency_id = journal.currency_id or journal.company_id.currency_id

    def _compute_current_balance(self):
        for journal in self:
            journal.current_balance = 0.0
            if journal.type in ("bank", "cash", "credit"):
                journal.current_balance, _line_count = journal._get_journal_bank_account_balance()
