from collections import defaultdict
from odoo import models


class SmartImportInventoryEngine(models.AbstractModel):
    _name = 'smart.import.inventory.engine'
    _description = 'Smart Import Inventory Engine (compat shim)'

    def build_plan(self, items_rows, bom_rows, mapping_profile=False, options=False):
        session = self.env['smart.import.session']
        payload = {
            'items_rows': items_rows,
            'bom_rows': bom_rows,
            'options': options or {},
            'dry_run': True,
            'caches': {},
            'stats': defaultdict(int),
            'issues': defaultdict(list),
            'errors': [],
        }
        pack = self.env['smart.import.pack.inventory_fulcrum']
        return pack._collect_plan_from_providers(session, payload)

    def execute(self, session, items_rows, bom_rows, options, dry_run=False):
        payload = {
            'session': session,
            'items_rows': items_rows,
            'bom_rows': bom_rows,
            'options': options or {},
            'dry_run': dry_run,
            'caches': {},
            'stats': defaultdict(int),
            'issues': defaultdict(list),
            'errors': [],
        }
        pack = self.env['smart.import.pack.inventory_fulcrum']
        for provider in pack.get_step_providers(pack._pack_code):
            provider.execute_steps(session, payload)
        return {
            'stats': dict(payload['stats']),
            'issues': {k: sorted(set(v)) for k, v in payload['issues'].items()},
            'errors': payload['errors'],
        }
