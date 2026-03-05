import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class SmartImportInventoryStockSteps(models.AbstractModel):
    _name = 'smart.import.step.inventory.stock'
    _description = 'Smart Import Inventory Stock Steps'

    _smart_import_step_provider = True
    _smart_import_pack_code = 'inventory_fulcrum'
    _provider_sequence = 20

    def build_plan_fragment(self, session, payload):
        items_rows = payload['items_rows']
        return {
            'steps': ['locations_putaway', 'products_routes', 'orderpoints'],
            'counts': {
                'unique_locations': len({r['default_location'] for r in items_rows if r['default_location']}),
                'orderpoints_count': len([r for r in items_rows if r['min_stock'] > 0]),
            },
            'issues': {},
            'mapped_fields': {
                'stock.warehouse.orderpoint': ['product_id', 'location_id', 'product_min_qty', 'product_max_qty', 'qty_multiple'],
                'stock.putaway.rule': ['product_id', 'location_in_id', 'location_out_id'],
            },
        }

    def execute_steps(self, session, payload):
        env = self.env
        items_rows = payload['items_rows']
        dry_run = payload['dry_run']
        stats = payload['stats']
        issues = payload['issues']

        session.append_log('INFO', _('[smart_import_stock][items] starting stock configuration'))
        _logger.info('[smart_import_stock][items] starting')

        company = env.company
        options = payload['options']
        warehouse = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        stock_location = warehouse.lot_stock_id if warehouse else env.ref('stock.stock_location_stock')
        buy_route = env['stock.route'].search([('name', '=', 'Buy'), ('company_id', 'in', [False, company.id])], limit=1)
        manufacture_route = env['stock.route'].search([('name', '=', 'Manufacture'), ('company_id', 'in', [False, company.id])], limit=1)

        tmpl_cache = payload['caches'].setdefault('product_tmpl_cache', {p.default_code: p for p in env['product.template'].search([('default_code', '!=', False)])})
        variant_cache = payload['caches'].setdefault('product_variant_cache', {code: tmpl.product_variant_id for code, tmpl in tmpl_cache.items() if tmpl.product_variant_id})
        location_cache = payload['caches'].setdefault('location_cache', {l.complete_name: l for l in env['stock.location'].search([('company_id', '=', company.id), ('usage', '=', 'internal')])})

        if options.get('create_locations_putaway'):
            for loc_name in sorted({r['default_location'] for r in items_rows if r['default_location']}):
                full_name = f'{stock_location.complete_name}/Fulcrum/{loc_name}'
                if full_name in location_cache:
                    continue
                if dry_run:
                    stats['location_would_create'] += 1
                else:
                    parent = env['stock.location'].search([('complete_name', '=', f'{stock_location.complete_name}/Fulcrum')], limit=1)
                    if not parent:
                        parent = env['stock.location'].create({'name': 'Fulcrum', 'usage': 'internal', 'location_id': stock_location.id, 'company_id': company.id})
                    new_loc = env['stock.location'].create({'name': loc_name, 'usage': 'internal', 'location_id': parent.id, 'company_id': company.id})
                    location_cache[new_loc.complete_name] = new_loc
                    stats['location_created'] += 1

        for row in items_rows:
            code = row['default_code']
            tmpl = tmpl_cache.get(code)
            if not tmpl:
                continue
            route_ids = set(tmpl.route_ids.ids)
            if row['buy_or_make'] == 'Buy' or row['vendor_name']:
                if buy_route:
                    route_ids.add(buy_route.id)
            if row['buy_or_make'] == 'Make' and manufacture_route:
                route_ids.add(manufacture_route.id)
            if route_ids:
                if dry_run:
                    stats['route_would_update'] += 1
                else:
                    tmpl.write({'route_ids': [(6, 0, sorted(route_ids))]})
                    stats['route_updated'] += 1

            if row['min_stock'] > 0 and variant_cache.get(code):
                product_variant = variant_cache[code]
                max_qty = row['min_stock'] * 2 if options.get('orderpoint_max_policy') == 'double_min' else row['min_stock']
                op_vals = {
                    'product_id': product_variant.id,
                    'location_id': stock_location.id,
                    'product_min_qty': row['min_stock'],
                    'product_max_qty': max_qty,
                    'qty_multiple': row['min_production_qty'] if row['min_production_qty'] > 0 else 1.0,
                    'company_id': company.id,
                }
                op = env['stock.warehouse.orderpoint'].search([
                    ('product_id', '=', product_variant.id),
                    ('location_id', '=', stock_location.id),
                    ('company_id', '=', company.id),
                ], limit=1)
                if op:
                    if dry_run:
                        stats['orderpoint_would_update'] += 1
                    else:
                        op.write(op_vals)
                        stats['orderpoint_updated'] += 1
                else:
                    if dry_run:
                        stats['orderpoint_would_create'] += 1
                    else:
                        env['stock.warehouse.orderpoint'].create(op_vals)
                        stats['orderpoint_created'] += 1

            if options.get('create_locations_putaway') and row['default_location'] and variant_cache.get(code):
                full_name = f'{stock_location.complete_name}/Fulcrum/{row["default_location"]}'
                dst_location = location_cache.get(full_name)
                if not dst_location:
                    issues['missing_putaway_locations'].append(full_name)
                    continue
                if dry_run:
                    stats['putaway_would_create'] += 1
                    continue
                putaway = env['stock.putaway.rule'].search([
                    ('product_id', '=', variant_cache[code].id),
                    ('location_in_id', '=', stock_location.id),
                    ('location_out_id', '=', dst_location.id),
                    ('company_id', '=', company.id),
                ], limit=1)
                if not putaway:
                    env['stock.putaway.rule'].create({
                        'product_id': variant_cache[code].id,
                        'location_in_id': stock_location.id,
                        'location_out_id': dst_location.id,
                        'company_id': company.id,
                    })
                    stats['putaway_created'] += 1

        session.append_log('INFO', _('[smart_import_stock][items] finished: orderpoints=%s putaway=%s') % (stats.get('orderpoint_created', 0), stats.get('putaway_created', 0)))
        session.post_summary_message(
            _('Smart Import Stock summary'),
            [
                _('Routes updated: %s') % stats.get('route_updated', 0),
                _('Orderpoints created: %s') % stats.get('orderpoint_created', 0),
                _('Putaway rules created: %s') % stats.get('putaway_created', 0),
            ],
        )
