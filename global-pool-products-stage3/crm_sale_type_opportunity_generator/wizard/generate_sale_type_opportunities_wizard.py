import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class GenerateSaleTypeOpportunitiesWizard(models.TransientModel):
    _name = 'generate.sale.type.opportunities.wizard'
    _description = 'Generate Sale Type Opportunities Wizard'

    team_id = fields.Many2one('crm.team', required=True)
    sale_type_id = fields.Many2one('sale.type', required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_('Start date must be before or equal to end date.'))

    def _get_partner_team_field(self):
        field = self.env['res.partner']._fields.get('x_studio_sales_team')
        if not field:
            raise UserError(
                _(
                    "Required Studio field 'x_studio_sales_team' is missing on contacts "
                    "(res.partner). Please add it before using this wizard."
                )
            )
        return field

    def _open_opportunity_domain(self, partner_id):
        return [
            ('type', '=', 'opportunity'),
            ('partner_id.commercial_partner_id', '=', partner_id),
            ('team_id', '=', self.team_id.id),
            ('active', '=', True),
            ('probability', '<', 100),
        ]

    def action_generate_opportunities(self):
        self.ensure_one()
        self._get_partner_team_field()

        _logger.info(
            "Generating opportunities from sales: team=%s sale_type=%s from=%s to=%s",
            self.team_id.display_name,
            self.sale_type_id.display_name,
            self.date_from,
            self.date_to,
        )

        date_start = fields.Datetime.to_datetime(self.date_from)
        date_end = fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)
        order_domain = [
            ('state', 'in', ['sale', 'done']),
            ('sale_type_id', '=', self.sale_type_id.id),
            ('date_order', '>=', date_start),
            ('date_order', '<', date_end),
            ('partner_id.commercial_partner_id.x_studio_sales_team', '=', self.team_id.id),
        ]
        sale_orders = self.env['sale.order'].search(order_domain)

        partner_stats = {}
        for order in sale_orders:
            commercial_partner = order.partner_id.commercial_partner_id
            stats = partner_stats.setdefault(
                commercial_partner.id,
                {'partner': commercial_partner, 'amount': 0.0, 'count': 0},
            )
            stats['amount'] += order.amount_untaxed
            stats['count'] += 1

        created_count = 0
        skipped_count = 0
        lead_obj = self.env['crm.lead']

        for stats in partner_stats.values():
            partner = stats['partner']
            if lead_obj.search_count(self._open_opportunity_domain(partner.id)):
                skipped_count += 1
                _logger.info(
                    "Skipping opportunity for %s: open opportunity already exists for team=%s",
                    partner.display_name,
                    self.team_id.display_name,
                )
                continue

            description = _(
                "Generated from Sale Type Opportunity wizard.\n"
                "Sale type: %(sale_type)s\n"
                "Date range: %(date_from)s to %(date_to)s\n"
                "Matched sale orders: %(order_count)s\n"
                "Total untaxed amount: %(amount).2f"
            ) % {
                'sale_type': self.sale_type_id.display_name,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'order_count': stats['count'],
                'amount': stats['amount'],
            }

            opportunity = lead_obj.create({
                'name': _('%(partner)s - %(sale_type)s Follow-up') % {
                    'partner': partner.name,
                    'sale_type': self.sale_type_id.display_name,
                },
                'type': 'opportunity',
                'partner_id': partner.id,
                'team_id': self.team_id.id,
                'sale_type_id': self.sale_type_id.id,
                'expected_revenue': stats['amount'],
                'description': description,
            })
            opportunity.message_post(
                body=_(
                    "Opportunity generated from sales history for sale type %(sale_type)s "
                    "and period %(date_from)s to %(date_to)s."
                ) % {
                    'sale_type': self.sale_type_id.display_name,
                    'date_from': self.date_from,
                    'date_to': self.date_to,
                }
            )
            created_count += 1

        total_matched = len(partner_stats)
        summary = _(
            "Sales opportunity generation complete. Matched customers: %(matched)s, "
            "created: %(created)s, skipped (existing open opportunities): %(skipped)s."
        ) % {
            'matched': total_matched,
            'created': created_count,
            'skipped': skipped_count,
        }
        _logger.info(summary)
        self.team_id.message_post(body=summary)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Opportunities Generated'),
                'message': summary,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
