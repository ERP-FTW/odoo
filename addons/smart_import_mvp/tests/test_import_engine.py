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
