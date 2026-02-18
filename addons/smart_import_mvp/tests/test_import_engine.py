import base64
import io

from openpyxl import Workbook

from odoo.tests.common import TransactionCase


class TestFulcrumImportEngine(TransactionCase):

    def _make_attachment(self, name, sheet_name, headers, rows):
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        ws.append(headers)
        for row in rows:
            ws.append(row)
        output = io.BytesIO()
        wb.save(output)
        return self.env['ir.attachment'].create({
            'name': name,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

    def test_build_plan_counts(self):
        engine = self.env['mlr.fulcrum.import.engine']
        items_attachment = self._make_attachment(
            'items.xlsx',
            'Filtered Items',
            ['Number', 'Description', 'UnitOfMeasureName', 'Category', 'IsSellItem', 'MinimumStockOnHand', 'ItemOrigin'],
            [
                ['A001', 'Product A', 'Units', 'Cat A', True, 2, 'Buy'],
                ['A002', 'Product B', 'Units', 'Cat A', False, 0, 'Make'],
            ],
        )
        bom_attachment = self._make_attachment(
            'bom.xlsx',
            'Sheet1',
            ['Parent Number', 'Child Number', 'Units Required'],
            [['A002', 'A001', 3]],
        )

        items_rows = engine.parse_items_xlsx(items_attachment)
        bom_rows = engine.parse_bom_xlsx(bom_attachment)
        plan = engine.build_plan(items_rows, bom_rows)

        self.assertEqual(plan['counts']['product_rows_count'], 2)
        self.assertEqual(plan['counts']['boms_count'], 1)
        self.assertEqual(plan['counts']['bom_lines_count'], 1)

    def test_dry_run_simulates_auto_created_dependencies(self):
        engine = self.env['mlr.fulcrum.import.engine']
        session = self.env['mlr.fulcrum.import.session'].create({})

        items_rows = [{
            'default_code': 'ASM-ELE-00002',
            'name': 'Assembly',
            'tags': '',
            'buy_or_make': 'Make',
            'min_stock': 1.0,
            'min_production_qty': 0.0,
            'uom_name': 'Piece',
            'category': 'New Cat',
            'sell_ok': False,
            'default_location': 'A1',
            'vendor_name': 'New Vendor',
            'vendor_price': 0.0,
            'vendor_moq': 0.0,
            'vendor_uom': 'Set',
            'raw': {},
        }]
        bom_rows = [{
            'parent_number': 'ASM-ELE-00002',
            'parent_description': 'Assembly',
            'child_number': 'ASM-ELE-00002',
            'child_description': 'Assembly',
            'units_required': 1.0,
        }]

        result = engine.execute(
            session,
            items_rows,
            bom_rows,
            {
                'auto_create_unknown_uom': True,
                'create_locations_putaway': True,
                'create_placeholder_missing_bom_children': False,
                'orderpoint_max_policy': 'same_as_min',
            },
            dry_run=True,
        )

        self.assertEqual(result['errors'], [])
        self.assertFalse(result['issues'].get('missing_bom_parents'))
        self.assertFalse(result['issues'].get('unknown_uoms'))
        self.assertEqual(result['stats'].get('uom_would_create'), 2)
        self.assertEqual(result['stats'].get('category_would_create'), 1)
        self.assertEqual(result['stats'].get('vendor_would_create'), 1)
        self.assertEqual(result['stats'].get('location_would_create'), 1)
        self.assertEqual(result['stats'].get('product_would_create'), 1)
        self.assertEqual(result['stats'].get('bom_would_process'), 1)
        self.assertEqual(result['stats'].get('orderpoint_would_create'), 1)


    def test_build_plan_resolves_common_uom_aliases(self):
        engine = self.env['mlr.fulcrum.import.engine']
        items_rows = [{
            'default_code': 'UOM-001',
            'name': 'Alias Product',
            'tags': '',
            'buy_or_make': 'Buy',
            'min_stock': 0.0,
            'min_production_qty': 0.0,
            'uom_name': 'Piece',
            'category': 'Cat',
            'sell_ok': True,
            'default_location': '',
            'vendor_name': '',
            'vendor_price': 0.0,
            'vendor_moq': 0.0,
            'vendor_uom': 'Kilogram',
            'raw': {},
        }]

        plan = engine.build_plan(items_rows, [])

        self.assertEqual(plan['issues']['unknown_uoms'], [])


    def test_parse_items_uses_mapping_profile_synonyms(self):
        engine = self.env['mlr.fulcrum.import.engine']
        profile = self.env.ref('smart_import_mvp.mapping_profile_fulcrum_default')
        items_attachment = self._make_attachment(
            'items_syn.xlsx',
            'Filtered Items',
            ['Number', 'Description', 'BuyOrMake', 'Unknown Header'],
            [['A100', 'Syn Product', 'Buy', 'Extra']],
        )

        rows = engine.parse_items_xlsx(items_attachment, mapping_profile=profile)

        self.assertEqual(rows[0]['default_code'], 'A100')
        self.assertEqual(rows[0]['name'], 'Syn Product')
        self.assertEqual(rows[0]['buy_or_make'], 'Buy')
        self.assertEqual(rows[0]['_extra_columns']['Unknown Header'], 'Extra')
