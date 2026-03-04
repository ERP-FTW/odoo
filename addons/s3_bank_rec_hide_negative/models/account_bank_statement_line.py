import logging

from odoo import api, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.model
    def _action_open_bank_reconciliation_widget(self, extra_domain=None, default_context=None, name=None, kanban_first=True):
        action = super()._action_open_bank_reconciliation_widget(
            extra_domain=extra_domain,
            default_context=default_context,
            name=name,
            kanban_first=kanban_first,
        )

        if self.env.user.has_group('s3_bank_rec_hide_negative.group_hide_negative_bank_rec_lines'):
            base_domain = action.get('domain', [])
            action['domain'] = expression.AND([base_domain, [('amount', '>=', 0)]])
            _logger.debug(
                "Applied bank reconciliation negative-line filter for user_id=%s (kanban_first=%s)",
                self.env.user.id,
                kanban_first,
            )

        return action
