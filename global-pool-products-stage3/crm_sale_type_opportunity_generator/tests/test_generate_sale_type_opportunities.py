from datetime import datetime
from unittest import SkipTest

from odoo import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install', '-at_install')
class TestGenerateSaleTypeOpportunities(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._ensure_sales_team_field()

        cls.team = cls.env['crm.team'].create({'name': 'North Team'})
        cls.other_team = cls.env['crm.team'].create({'name': 'South Team'})

        cls.sale_type_a = cls.env['sale.type'].create({'name': 'Retail'})
        cls.sale_type_b = cls.env['sale.type'].create({'name': 'Wholesale'})

        cls.product = cls.env['product.product'].create({'name': 'Service A', 'list_price': 100.0})

        cls.partner_company_1 = cls.env['res.partner'].create({
            'name': 'ACME Corp',
            'x_studio_sales_team': cls.team.id,
        })
        cls.partner_contact_1 = cls.env['res.partner'].create({
            'name': 'ACME Contact',
            'parent_id': cls.partner_company_1.id,
            'x_studio_sales_team': cls.team.id,
        })
        cls.partner_company_2 = cls.env['res.partner'].create({
            'name': 'Beta Corp',
            'x_studio_sales_team': cls.team.id,
        })
        cls.partner_other_team = cls.env['res.partner'].create({
            'name': 'Gamma Corp',
            'x_studio_sales_team': cls.other_team.id,
        })

        cls._create_order(cls.partner_contact_1, cls.sale_type_a, datetime(2024, 1, 10, 10, 0, 0), 100.0)
        cls._create_order(cls.partner_company_1, cls.sale_type_a, datetime(2024, 1, 20, 10, 0, 0), 200.0)
        cls._create_order(cls.partner_company_1, cls.sale_type_b, datetime(2024, 1, 15, 10, 0, 0), 999.0)
        cls._create_order(cls.partner_company_2, cls.sale_type_a, datetime(2024, 1, 12, 10, 0, 0), 150.0)
        cls._create_order(cls.partner_company_2, cls.sale_type_a, datetime(2023, 12, 20, 10, 0, 0), 111.0)
        cls._create_order(cls.partner_other_team, cls.sale_type_a, datetime(2024, 1, 14, 10, 0, 0), 333.0)

        cls.existing_open = cls.env['crm.lead'].create({
            'name': 'Existing Beta Opportunity',
            'type': 'opportunity',
            'partner_id': cls.partner_company_2.id,
            'team_id': cls.team.id,
            'sale_type_id': cls.sale_type_b.id,
            'probability': 50,
            'expected_revenue': 20.0,
        })

    @classmethod
    def _ensure_sales_team_field(cls):
        if cls.env['res.partner']._fields.get('x_studio_sales_team'):
            return

        model = cls.env['ir.model']._get('res.partner')
        cls.env['ir.model.fields'].create({
            'name': 'x_studio_sales_team',
            'field_description': 'Sales Team',
            'model_id': model.id,
            'model': 'res.partner',
            'ttype': 'many2one',
            'relation': 'crm.team',
            'state': 'manual',
        })
        cls.env.registry.clear_cache()
        if not cls.env['res.partner']._fields.get('x_studio_sales_team'):
            raise SkipTest("Field x_studio_sales_team is required for these tests")

    @classmethod
    def _create_order(cls, partner, sale_type, date_order, amount):
        order = cls.env['sale.order'].create({
            'partner_id': partner.id,
            'date_order': date_order,
            'sale_type_id': sale_type.id,
            'order_line': [Command.create({
                'name': cls.product.name,
                'product_id': cls.product.id,
                'product_uom_qty': 1.0,
                'price_unit': amount,
            })],
        })
        order.action_confirm()
        return order

    def test_generate_opportunities(self):
        wizard = self.env['generate.sale.type.opportunities.wizard'].create({
            'team_id': self.team.id,
            'sale_type_id': self.sale_type_a.id,
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })

        result = wizard.action_generate_opportunities()

        self.assertEqual(result['tag'], 'display_notification')
        self.assertIn('Matched customers: 2', result['params']['message'])
        self.assertIn('created: 1', result['params']['message'])
        self.assertIn('skipped', result['params']['message'])

        opportunities = self.env['crm.lead'].search([
            ('type', '=', 'opportunity'),
            ('team_id', '=', self.team.id),
            ('sale_type_id', '=', self.sale_type_a.id),
        ])
        self.assertEqual(len(opportunities), 1)

        created_opportunity = opportunities
        self.assertEqual(len(created_opportunity), 1)
        self.assertEqual(created_opportunity.partner_id, self.partner_company_1)
        self.assertEqual(created_opportunity.expected_revenue, 300.0)

        self.assertFalse(
            self.env['crm.lead'].search([
                ('partner_id.commercial_partner_id', '=', self.partner_company_2.id),
                ('team_id', '=', self.team.id),
                ('sale_type_id', '=', self.sale_type_a.id),
                ('type', '=', 'opportunity'),
            ])
        )

        self.assertFalse(
            self.env['crm.lead'].search([
                ('partner_id', '=', self.partner_other_team.id),
                ('team_id', '=', self.team.id),
                ('sale_type_id', '=', self.sale_type_a.id),
                ('type', '=', 'opportunity'),
            ])
        )
