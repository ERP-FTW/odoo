from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        super()._fill_sale_purchase_dashboard_data(dashboard_data)
        for journal in self.filtered(lambda j: j.type in ('sale', 'purchase')):
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            dashboard_data[journal.id].update({
                'balance': currency.format(journal.default_account_id.current_balance),
                'show_balance': True,
            })

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        for journal in self.filtered(lambda j: j.type in ('bank', 'cash', 'credit')):
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            dashboard_data[journal.id].update({
                'balance': currency.format(journal.default_account_id.current_balance),
                'show_balance': True,
            })

    def _fill_general_dashboard_data(self, dashboard_data):
        super()._fill_general_dashboard_data(dashboard_data)
        for journal in self.filtered(lambda j: j.type == 'general'):
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            dashboard_data[journal.id].update({
                'balance': currency.format(journal.default_account_id.current_balance),
                'show_balance': True,
            })
