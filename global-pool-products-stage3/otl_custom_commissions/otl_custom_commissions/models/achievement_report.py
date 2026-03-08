from odoo import models, fields, api, _

class SaleAchievementReport(models.Model):
    _inherit = 'sale.commission.achievement.report'

    def _get_invoices_rates(self):
        return ['amount_invoiced', 'qty_invoiced', 'amount_paid']


    def _get_invoice_rates_product(self):
        # SQL CASE statement to calculate commission based on invoice state and payment state
        return """
            CASE
                WHEN am.move_type = 'out_invoice' THEN
                    -- For 'out_invoice' (sales invoices), calculate commission based on amount invoiced and paid
                    rules.amount_invoiced_rate * aml.price_subtotal / am.invoice_currency_rate +
                    rules.qty_invoiced_rate * aml.quantity +
                    rules.amount_paid_rate * (am.amount_total - COALESCE(am.amount_residual, 0)) / am.invoice_currency_rate
                WHEN am.move_type = 'out_refund' THEN
                    -- For 'out_refund' (refund invoices), calculate commission with a negative sign
                    (rules.amount_invoiced_rate * aml.price_subtotal / am.invoice_currency_rate +
                    rules.qty_invoiced_rate * aml.quantity +
                    rules.amount_paid_rate * (am.amount_total - COALESCE(am.amount_residual, 0)) / am.invoice_currency_rate) * -1
                WHEN am.payment_state IN ('in_payment') THEN
                    -- For invoices with 'paid', 'partial', or 'in_payment' state, calculate commission as usual
                    rules.amount_invoiced_rate * aml.price_subtotal / am.invoice_currency_rate +
                    rules.qty_invoiced_rate * aml.quantity +
                    rules.amount_paid_rate * (am.amount_total - COALESCE(am.amount_residual, 0)) / am.invoice_currency_rate
            END
        """
    def _invoices_lines(self, users=None, teams=None):
        return f"""
        invoices_rules AS (
            SELECT
                COALESCE(scpu.date_from, scp.date_from) AS date_from,
                COALESCE(scpu.date_to, scp.date_to) AS date_to,
                scpu.user_id AS user_id,
                scp.team_id AS team_id,
                scp.id AS plan_id,
                scpa.product_id,
                scpa.product_categ_id,
                scpa.customer_id,
                scp.company_id,
                scp.currency_id,
                scp.user_type = 'team' AS team_rule,
                {self._rate_to_case(self._get_invoices_rates())}
                {self._select_rules()}
            FROM sale_commission_plan_achievement scpa
            JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
            JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
            WHERE scp.active
              AND scp.state = 'approved'
              AND scpa.type IN ({','.join("'%s'" % r for r in self._get_invoices_rates())})
            {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
        ), invoice_commission_lines_team AS (
            SELECT
                {self._select_invoices()}
            FROM invoices_rules rules
                 {self._join_invoices()}
            WHERE {self._where_invoices()}
              AND rules.team_rule
              AND am.team_id = rules.team_id
            {'AND am.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
              AND am.date BETWEEN rules.date_from AND rules.date_to
              AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
              AND (rules.customer_id = am.partner_id)
              AND (am.payment_state IN ('paid', 'partial','in_payment') OR rules.amount_paid_rate = 0)
            GROUP BY
                am.id,
                rules.plan_id,
                rules.user_id,
                rules.product_categ_id,
                rules.customer_id
        ), invoice_commission_lines_user AS (
            SELECT
                {self._select_invoices()}
            FROM invoices_rules rules
                 {self._join_invoices()}
            WHERE {self._where_invoices()}
              AND NOT rules.team_rule
              AND am.invoice_user_id = rules.user_id
            {'AND am.invoice_user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
              AND am.date BETWEEN rules.date_from AND rules.date_to
              AND (rules.product_id IS NULL OR rules.product_id = aml.product_id)
              AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
              AND (rules.customer_id = am.partner_id)
              AND (am.payment_state IN ('paid', 'partial','in_payment') OR rules.amount_paid_rate = 0)
            GROUP BY
                am.id,
                rules.plan_id,
                rules.user_id,
                rules.product_categ_id,
                rules.customer_id
        ), invoice_commission_lines AS (
            (SELECT *, 'account.move' AS related_res_model FROM invoice_commission_lines_team)
            UNION ALL
            (SELECT *, 'account.move' AS related_res_model FROM invoice_commission_lines_user)
        )""", 'invoice_commission_lines'