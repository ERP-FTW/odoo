import logging
from collections import defaultdict

from odoo import _, models

_logger = logging.getLogger(__name__)


class SmartImportInventoryMrpSteps(models.AbstractModel):
    _name = 'smart.import.step.inventory.mrp'
    _description = 'Smart Import Inventory MRP Steps'

    _smart_import_step_provider = True
    _smart_import_pack_code = 'inventory_fulcrum'
    _provider_sequence = 30

    def build_plan_fragment(self, session, payload):
        bom_rows = payload['bom_rows']
        grouped_boms = defaultdict(list)
        for row in bom_rows:
            if row['parent_number']:
                grouped_boms[row['parent_number']].append(row)
        return {
            'steps': ['boms'],
            'counts': {
                'boms_count': len(grouped_boms),
                'bom_lines_count': len(bom_rows),
            },
            'issues': {},
            'mapped_fields': {
                'mrp.bom': ['product_tmpl_id'],
                'mrp.bom.line': ['product_id', 'product_qty', 'product_uom_id'],
            },
        }

    def execute_steps(self, session, payload):
        env = self.env
        bom_rows = payload['bom_rows']
        options = payload['options']
        dry_run = payload['dry_run']
        stats = payload['stats']
        issues = payload['issues']
        errors = payload['errors']
        company = env.company

        session.append_log('INFO', _('[smart_import_mrp][bom] starting BOM import'))
        _logger.info('[smart_import_mrp][bom] starting')

        tmpl_cache = payload['caches'].setdefault('product_tmpl_cache', {p.default_code: p for p in env['product.template'].search([('default_code', '!=', False)])})
        variant_cache = payload['caches'].setdefault('product_variant_cache', {code: tmpl.product_variant_id for code, tmpl in tmpl_cache.items() if tmpl.product_variant_id})

        boms_by_parent = defaultdict(list)
        for row in bom_rows:
            if row['parent_number']:
                boms_by_parent[row['parent_number']].append(row)

        for parent_code, lines in boms_by_parent.items():
            parent_tmpl = tmpl_cache.get(parent_code)
            if not parent_tmpl:
                issues['missing_bom_parents'].append(parent_code)
                errors.append({'type': 'mrp:bom', 'key': parent_code, 'error': 'Missing parent product'})
                continue
            if dry_run:
                stats['bom_would_process'] += 1
                continue
            bom = env['mrp.bom'].search([
                ('product_tmpl_id', '=', parent_tmpl.id),
                ('company_id', 'in', [False, company.id]),
                ('type', '=', 'normal'),
            ], limit=1)
            if not bom:
                bom = env['mrp.bom'].create({'product_tmpl_id': parent_tmpl.id, 'product_qty': 1.0, 'type': 'normal', 'company_id': company.id})
                stats['bom_created'] += 1
            else:
                stats['bom_updated'] += 1
                bom.bom_line_ids.unlink()

            for line in lines:
                child_code = line['child_number']
                child_product = variant_cache.get(child_code)
                if not child_product:
                    if options.get('create_placeholder_missing_bom_children') and child_code:
                        child_tmpl = env['product.template'].create({
                            'default_code': child_code,
                            'name': line['child_description'] or child_code,
                            'type': 'consu',
                            'sale_ok': False,
                            'purchase_ok': False,
                        })
                        child_product = child_tmpl.product_variant_id
                        tmpl_cache[child_code] = child_tmpl
                        variant_cache[child_code] = child_product
                        stats['placeholder_products_created'] += 1
                    else:
                        issues['missing_bom_children'].append(child_code)
                        errors.append({'type': 'mrp:bom_line', 'key': f'{parent_code}->{child_code}', 'error': 'Missing child product'})
                        continue
                env['mrp.bom.line'].create({
                    'bom_id': bom.id,
                    'product_id': child_product.id,
                    'product_qty': line['units_required'] or 1.0,
                    'product_uom_id': child_product.uom_id.id,
                })
                stats['bom_line_created'] += 1

        session.append_log('INFO', _('[smart_import_mrp][bom] finished: boms=%s lines=%s') % (stats.get('bom_created', 0), stats.get('bom_line_created', 0)))
        session.post_summary_message(
            _('Smart Import MRP summary'),
            [
                _('BOMs created: %s') % stats.get('bom_created', 0),
                _('BOMs updated: %s') % stats.get('bom_updated', 0),
                _('BOM lines created: %s') % stats.get('bom_line_created', 0),
            ],
        )
