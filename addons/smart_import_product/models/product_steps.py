import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class SmartImportInventoryProductSteps(models.AbstractModel):
    _name = 'smart.import.step.inventory.product'
    _description = 'Smart Import Inventory Product Steps'

    _smart_import_step_provider = True
    _smart_import_pack_code = 'inventory_fulcrum'
    _provider_sequence = 10

    def _normalized(self, value):
        return str(value or '').strip()

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        return str(value or '').strip().lower() in ('1', 'true', 'yes', 'y')

    def _to_float(self, value):
        if value in (False, None, ''):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _uom_key(self, value):
        return self._normalized(value).lower()

    def _build_uom_alias_cache(self, env):
        alias_cache = {}
        aliases_by_xmlid = {
            'uom.product_uom_unit': ['piece', 'pieces', 'unit', 'units', 'set', 'sets'],
            'uom.product_uom_kgm': ['kg', 'kilogram', 'kilograms'],
            'uom.product_uom_litre': ['l', 'liter', 'litre'],
        }
        for xmlid, aliases in aliases_by_xmlid.items():
            uom = env.ref(xmlid, raise_if_not_found=False)
            if not uom:
                continue
            alias_cache[self._uom_key(uom.name)] = uom
            for alias in aliases:
                alias_cache[self._uom_key(alias)] = uom
        return alias_cache

    def _resolve_uom(self, uom_name, uom_cache, uom_alias_cache):
        if not uom_name:
            return False
        if uom_name in uom_cache:
            return uom_cache[uom_name]
        alias_uom = uom_alias_cache.get(self._uom_key(uom_name))
        if alias_uom:
            uom_cache[uom_name] = alias_uom
            return alias_uom
        return False

    def build_plan_fragment(self, session, payload):
        items_rows = payload['items_rows']
        uom_cache = {u.name: u for u in self.env['uom.uom'].search([])}
        alias_cache = self._build_uom_alias_cache(self.env)
        unknown_uoms = []
        for row in items_rows:
            for uom_name in (row['uom_name'], row['vendor_uom']):
                if uom_name and not self._resolve_uom(uom_name, uom_cache, alias_cache):
                    unknown_uoms.append(uom_name)
        return {
            'steps': ['uoms', 'categories', 'products', 'vendors'],
            'counts': {
                'unique_uoms': len({r['uom_name'] for r in items_rows if r['uom_name']}),
                'unique_categories': len({r['category'] for r in items_rows if r['category']}),
                'product_rows_count': len(items_rows),
                'unique_vendors': len({r['vendor_name'] for r in items_rows if r['vendor_name']}),
            },
            'issues': {
                'unknown_uoms': sorted(set(unknown_uoms)),
                'rows_without_product_number': [idx + 2 for idx, row in enumerate(items_rows) if not row['default_code']],
            },
            'mapped_fields': {
                'product.template': ['default_code', 'name', 'categ_id', 'uom_id', 'uom_po_id', 'sale_ok', 'purchase_ok', 'type'],
            },
        }

    def execute_steps(self, session, payload):
        env = self.env
        items_rows = payload['items_rows']
        options = payload['options']
        dry_run = payload['dry_run']
        stats = payload['stats']
        issues = payload['issues']
        errors = payload['errors']

        session.append_log('INFO', _('[smart_import_product][items] starting products import'))
        _logger.info('[smart_import_product][items] starting')

        uom_cache = payload['caches'].setdefault('uom_cache', {u.name: u for u in env['uom.uom'].search([])})
        uom_alias_cache = payload['caches'].setdefault('uom_alias_cache', self._build_uom_alias_cache(env))
        categ_cache = payload['caches'].setdefault('categ_cache', {c.name: c for c in env['product.category'].search([])})
        tmpl_cache = payload['caches'].setdefault('product_tmpl_cache', {p.default_code: p for p in env['product.template'].search([('default_code', '!=', False)])})
        variant_cache = payload['caches'].setdefault('product_variant_cache', {code: tmpl.product_variant_id for code, tmpl in tmpl_cache.items() if tmpl.product_variant_id})

        ref_uom = env.ref('uom.product_uom_unit')
        all_uoms = sorted({r['uom_name'] for r in items_rows if r['uom_name']} | {r['vendor_uom'] for r in items_rows if r['vendor_uom']})
        for uom_name in all_uoms:
            if self._resolve_uom(uom_name, uom_cache, uom_alias_cache):
                continue
            if not options.get('auto_create_unknown_uom'):
                issues['unknown_uoms'].append(uom_name)
                errors.append({'type': 'product:uom', 'key': uom_name, 'error': 'Unknown UoM'})
                continue
            if dry_run:
                stats['uom_would_create'] += 1
                continue
            uom = env['uom.uom'].create({
                'name': uom_name,
                'category_id': ref_uom.category_id.id,
                'uom_type': 'bigger' if options.get('new_uom_default_type') == 'bigger' else 'reference',
                'factor_inv': self._to_float(options.get('new_uom_default_factor_inv') or 1.0),
                'rounding': 0.01,
            })
            uom_cache[uom_name] = uom
            stats['uom_created'] += 1

        for categ_name in sorted({r['category'] for r in items_rows if r['category']}):
            if categ_name in categ_cache:
                continue
            if dry_run:
                stats['category_would_create'] += 1
                continue
            categ_cache[categ_name] = env['product.category'].create({'name': categ_name})
            stats['category_created'] += 1

        for row in items_rows:
            code = row['default_code']
            if not code:
                issues['rows_without_product_number'].append(row.get('name') or 'unknown')
                continue
            uom = self._resolve_uom(row['uom_name'], uom_cache, uom_alias_cache) if row['uom_name'] else ref_uom
            if row['uom_name'] and not uom:
                errors.append({'type': 'product', 'key': code, 'error': f"Unknown UoM '{row['uom_name']}'"})
                issues['unknown_uoms'].append(row['uom_name'])
                continue
            categ = categ_cache.get(row['category']) if row['category'] else False
            vals = {
                'default_code': code,
                'name': row['name'] or code,
                'uom_id': uom.id,
                'uom_po_id': uom.id,
                'type': 'consu',
                'sale_ok': bool(row['sell_ok']),
                'purchase_ok': row['buy_or_make'] == 'Buy' or bool(row['vendor_name']),
            }
            if categ:
                vals['categ_id'] = categ.id

            tmpl = tmpl_cache.get(code)
            if tmpl:
                if dry_run:
                    stats['product_would_update'] += 1
                else:
                    tmpl.write(vals)
                    stats['product_updated'] += 1
            else:
                if dry_run:
                    stats['product_would_create'] += 1
                    continue
                tmpl = env['product.template'].create(vals)
                tmpl_cache[code] = tmpl
                variant_cache[code] = tmpl.product_variant_id
                stats['product_created'] += 1

            if row.get('vendor_name'):
                issues['vendor_step_skipped'].append(row['vendor_name'])

        session.append_log('INFO', _('[smart_import_product][items] finished: created=%s updated=%s') % (stats.get('product_created', 0), stats.get('product_updated', 0)))
        session.post_summary_message(
            _('Smart Import Product summary'),
            [
                _('Products created: %s') % stats.get('product_created', 0),
                _('Products updated: %s') % stats.get('product_updated', 0),
                _('Unknown UoMs: %s') % len(set(issues.get('unknown_uoms', []))),
            ],
        )
