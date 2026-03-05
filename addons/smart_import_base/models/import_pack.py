from odoo import api, models


class SmartImportPack(models.AbstractModel):
    _name = 'smart.import.pack'
    _description = 'Smart Import Pack'

    _smart_import_pack = True
    _pack_code = False
    _pack_name = False

    def get_pack_code(self):
        return self._pack_code

    def get_pack_name(self):
        return self._pack_name or self._pack_code

    def detect(self, session):
        return {}

    def build_plan(self, session, dry_run=True):
        return {'stats': {}, 'issues': {}}

    def execute(self, session, dry_run=False):
        return {'stats': {}, 'issues': {}, 'errors': []}

    @api.model
    def available_packs(self):
        packs = []
        for model_name in sorted(self.env.registry.models):
            model = self.env[model_name]
            if model_name == 'smart.import.pack' or not getattr(model, '_smart_import_pack', False):
                continue
            code = model.get_pack_code()
            if not code:
                continue
            packs.append((code, model.get_pack_name(), model_name))
        return packs

    @api.model
    def get_pack(self, code):
        for pack_code, _pack_name, model_name in self.available_packs():
            if pack_code == code:
                return self.env[model_name]
        return self.env['smart.import.pack']

    @api.model
    def get_step_providers(self, pack_code):
        providers = []
        for model_name in sorted(self.env.registry.models):
            model = self.env[model_name]
            if not getattr(model, '_smart_import_step_provider', False):
                continue
            if getattr(model, '_smart_import_pack_code', False) != pack_code:
                continue
            providers.append((getattr(model, '_provider_sequence', 100), model_name, model))
        providers.sort(key=lambda item: (item[0], item[1]))
        return [provider for _seq, _name, provider in providers]
