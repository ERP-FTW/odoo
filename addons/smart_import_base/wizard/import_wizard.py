import json

from odoo import _, fields, models
from odoo.exceptions import UserError


class SmartImportWizard(models.TransientModel):
    _name = 'smart.import.wizard'
    _description = 'Smart Import Wizard'

    step = fields.Selection([('upload', 'Upload'), ('review', 'Review')], default='upload', required=True)
    pack_code = fields.Selection(selection='_selection_pack_code', string='Import Pack', required=True)
    mapping_profile_id = fields.Many2one('smart.import.mapping.profile', domain="[('active', '=', True)]")
    attachment_ids = fields.Many2many('ir.attachment', string='Files')
    dry_run = fields.Boolean(default=True)

    session_id = fields.Many2one('smart.import.session', readonly=True)
    session_file_line_ids = fields.One2many(related='session_id.file_line_ids', readonly=True)
    plan_text = fields.Text(readonly=True)
    issues_text = fields.Text(readonly=True)

    def _selection_pack_code(self):
        return [(code, name) for code, name, _model in self.env['smart.import.pack'].available_packs()]

    def _open_self(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Smart Import'),
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    def _prepare_file_line_vals(self, session, attachment):
        helper = self.env['smart.import.xlsx.helper']
        sheet_names = helper.get_sheet_names(attachment)
        first_sheet = sheet_names[0] if sheet_names else False
        headers = helper.read_headers(attachment, sheet_name=first_sheet, header_row_guess=1)
        previews = helper.read_preview_rows(attachment, sheet_name=first_sheet, n=10, header_row=1)
        return {
            'session_id': session.id,
            'attachment_id': attachment.id,
            'filename': attachment.name,
            'mimetype': attachment.mimetype,
            'kind': 'unknown',
            'sheet_names_json': json.dumps(sheet_names),
            'detected_sheets_json': json.dumps([first_sheet] if first_sheet else []),
            'header_row_json': json.dumps(headers),
            'preview_rows_json': json.dumps(previews),
            'detected_models_json': json.dumps([]),
        }

    def action_analyze_files(self):
        self.ensure_one()
        if not self.attachment_ids:
            raise UserError(_('Please upload at least one XLSX file.'))

        session = self.session_id or self.env['smart.import.session'].create({
            'mapping_profile_id': self.mapping_profile_id.id,
        })
        session.write({
            'state': 'draft',
            'mapping_profile_id': self.mapping_profile_id.id,
            'options_json': json.dumps({'dry_run': self.dry_run, 'pack_code': self.pack_code, 'mapping_profile_id': self.mapping_profile_id.id}),
            'stats_json': False,
            'issues_json': False,
            'error_csv_attachment_id': False,
            'log_text': False,
        })
        session.file_line_ids.unlink()

        for attachment in self.attachment_ids:
            self.env['smart.import.session.file'].create(self._prepare_file_line_vals(session, attachment))

        pack = self.env['smart.import.pack'].get_pack(self.pack_code)
        session.append_log('INFO', _('Calling detect for pack %s') % self.pack_code)
        detect_payload = pack.detect(session)
        if detect_payload:
            session.append_log('INFO', _('Detection summary: %s') % json.dumps(detect_payload, sort_keys=True))

        session.append_log('INFO', _('Calling build_plan for pack %s') % self.pack_code)
        result = pack.build_plan(session, dry_run=True)
        session.set_stats(result.get('stats', {}))
        session.set_issues(result.get('issues', {}))
        session.state = 'planned'

        self.write({
            'session_id': session.id,
            'step': 'review',
            'plan_text': session.stats_pretty,
            'issues_text': session.issues_pretty,
        })
        return self._open_self()

    def action_back_to_upload(self):
        self.step = 'upload'
        return self._open_self()

    def action_run_import(self):
        self.ensure_one()
        if not self.session_id:
            raise UserError(_('Analyze files first.'))
        pack = self.env['smart.import.pack'].get_pack(self.pack_code)
        self.session_id.append_log('INFO', _('Calling execute for pack %s (dry_run=%s)') % (self.pack_code, self.dry_run))
        result = pack.execute(self.session_id, dry_run=self.dry_run)
        self.session_id.set_stats(result.get('stats', {}))
        self.session_id.set_issues(result.get('issues', {}))
        self.session_id.state = 'planned' if self.dry_run else ('error' if result.get('errors') else 'done')
        self.write({'plan_text': self.session_id.stats_pretty, 'issues_text': self.session_id.issues_pretty})
        return self._open_self()
