import base64
import io
import json
import logging
from collections import defaultdict

from openpyxl import load_workbook

from odoo import _, models

_logger = logging.getLogger(__name__)


class SmartImportPackInventoryFulcrum(models.AbstractModel):
    _name = 'smart.import.pack.inventory_fulcrum'
    _inherit = 'smart.import.pack'
    _description = 'Smart Import Pack Inventory Fulcrum'

    _pack_code = 'inventory_fulcrum'
    _pack_name = 'Inventory (Fulcrum)'

    def _normalized(self, value):
        return str(value or '').strip()

    def _to_float(self, value):
        if value in (False, None, ''):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        return str(value or '').strip().lower() in ('1', 'true', 'yes', 'y')

    def _header_lookup_key(self, value):
        return self._normalized(value).lower()

    def _build_header_map(self, headers, mapping_profile=False):
        profile = mapping_profile
        header_map = {}
        if not profile:
            return header_map
        keyword_map = {}
        for keyword in profile.keyword_ids.filtered('active'):
            key = self._header_lookup_key(keyword.source_key)
            if key and (key not in keyword_map or keyword.priority < keyword_map[key].priority):
                keyword_map[key] = keyword
        for header in headers:
            match = keyword_map.get(self._header_lookup_key(header))
            if match:
                header_map[header] = match.canonical_key
        return header_map

    def _detect_file_kind(self, headers):
        header_keys = {self._header_lookup_key(h) for h in headers if h}
        if {'parent number', 'child number', 'units required'}.issubset(header_keys):
            return 'bom', [{'model': 'mrp.bom', 'confidence': 0.99}, {'model': 'mrp.bom.line', 'confidence': 0.99}]
        if {'number', 'description'}.issubset(header_keys):
            return 'items', [
                {'model': 'product.template', 'confidence': 0.95},
                {'model': 'stock.warehouse.orderpoint', 'confidence': 0.7},
            ]
        return 'unknown', []

    def detect(self, session):
        summary = {'items': 0, 'bom': 0, 'unknown': 0}
        for line in session.file_line_ids:
            headers = json.loads(line.header_row_json or '[]')
            kind, models_payload = self._detect_file_kind(headers)
            line.write({'kind': kind, 'detected_models_json': json.dumps(models_payload)})
            summary[kind] += 1
        session.append_log('INFO', _('Inventory pack detect complete.'))
        return summary

    def parse_items_xlsx(self, attachment, mapping_profile=False):
        data = base64.b64decode(attachment.datas)
        workbook = load_workbook(io.BytesIO(data), data_only=True)
        sheet = workbook['Sheet1'] if 'Sheet1' in workbook.sheetnames else workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [self._normalized(head) for head in rows[0]]
        header_map = self._build_header_map(headers, mapping_profile=mapping_profile)
        parsed_rows = []
        for row in rows[1:]:
            if not any(row):
                continue
            vals = {headers[idx]: row[idx] if idx < len(row) else False for idx in range(len(headers))}
            canonical_vals = {}
            for header, canonical_key in header_map.items():
                canonical_vals[canonical_key] = vals.get(header)
            parsed_rows.append({
                'default_code': self._normalized(canonical_vals.get('default_code')),
                'name': self._normalized(canonical_vals.get('name')),
                'category': self._normalized(canonical_vals.get('category')),
                'uom_name': self._normalized(canonical_vals.get('uom_name')),
                'vendor_name': self._normalized(canonical_vals.get('vendor_name')),
                'vendor_price': self._to_float(canonical_vals.get('vendor_price')),
                'vendor_moq': self._to_float(canonical_vals.get('vendor_moq')),
                'vendor_uom': self._normalized(canonical_vals.get('vendor_uom')),
                'default_location': self._normalized(canonical_vals.get('default_location')),
                'min_stock': self._to_float(canonical_vals.get('min_stock')),
                'min_production_qty': self._to_float(canonical_vals.get('min_production_qty')),
                'sell_ok': self._to_bool(canonical_vals.get('sell_ok')),
                'buy_or_make': self._normalized(canonical_vals.get('buy_or_make')),
            })
        return parsed_rows

    def parse_bom_xlsx(self, attachment):
        data = base64.b64decode(attachment.datas)
        workbook = load_workbook(io.BytesIO(data), data_only=True)
        sheet = workbook['Sheet1'] if 'Sheet1' in workbook.sheetnames else workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [self._normalized(head) for head in rows[0]]
        parsed_rows = []
        for row in rows[1:]:
            if not any(row):
                continue
            vals = {headers[idx]: row[idx] if idx < len(row) else False for idx in range(len(headers))}
            parsed_rows.append({
                'parent_number': self._normalized(vals.get('Parent Number')),
                'parent_description': self._normalized(vals.get('Parent Description')),
                'child_number': self._normalized(vals.get('Child Number')),
                'child_description': self._normalized(vals.get('Child Description')),
                'units_required': self._to_float(vals.get('Units Required')) or 1.0,
            })
        return parsed_rows

    def _get_rows_from_session(self, session):
        profile = session.mapping_profile_id
        items_rows, bom_rows = [], []
        for line in session.file_line_ids:
            if line.kind == 'items':
                items_rows.extend(self.parse_items_xlsx(line.attachment_id, mapping_profile=profile))
            elif line.kind == 'bom':
                bom_rows.extend(self.parse_bom_xlsx(line.attachment_id))
        return items_rows, bom_rows

    def _init_payload(self, session, dry_run):
        options = json.loads(session.options_json or '{}')
        options.update({'mapping_profile_id': session.mapping_profile_id.id})
        items_rows, bom_rows = self._get_rows_from_session(session)
        return {
            'session': session,
            'items_rows': items_rows,
            'bom_rows': bom_rows,
            'options': options,
            'dry_run': dry_run,
            'caches': {},
            'stats': defaultdict(int),
            'issues': defaultdict(list),
            'errors': [],
        }

    def _collect_plan_from_providers(self, session, payload):
        plan = {'steps': [], 'counts': {}, 'issues': {}, 'mapped_fields': {}}
        for provider in self.get_step_providers(self._pack_code):
            fragment = provider.build_plan_fragment(session, payload) or {}
            plan['steps'].extend(fragment.get('steps', []))
            plan['counts'].update(fragment.get('counts', {}))
            plan['mapped_fields'].update(fragment.get('mapped_fields', {}))
            for key, val in (fragment.get('issues') or {}).items():
                plan['issues'].setdefault(key, [])
                if isinstance(val, list):
                    plan['issues'][key].extend(val)
                else:
                    plan['issues'][key] = val
        return plan

    def build_plan(self, session, dry_run=True):
        payload = self._init_payload(session, dry_run=True)
        plan = self._collect_plan_from_providers(session, payload)
        plan['issues'] = {k: sorted(set(v)) if isinstance(v, list) else v for k, v in plan['issues'].items()}
        session.append_log('INFO', _('Plan built from %s providers.') % len(self.get_step_providers(self._pack_code)))
        return {'stats': plan, 'issues': plan['issues'], 'dry_run': dry_run}

    def execute(self, session, dry_run=False):
        payload = self._init_payload(session, dry_run=dry_run)
        providers = self.get_step_providers(self._pack_code)
        for provider in providers:
            provider.execute_steps(session, payload)

        stats = dict(payload['stats'])
        issues = {k: sorted(set(filter(None, v))) for k, v in payload['issues'].items()}
        errors = payload['errors']
        if errors:
            session.make_error_csv(errors)
            session.append_log('WARNING', _('[smart_import_inventory] issues.csv generated with %s rows') % len(errors))

        session.append_log('INFO', _('[smart_import_inventory] execution finished. providers=%s') % len(providers))
        _logger.info('[smart_import_inventory] execution finished providers=%s errors=%s', len(providers), len(errors))
        return {'stats': stats, 'issues': issues, 'errors': errors}
