import base64
import csv
import io
import json

from odoo import api, fields, models


class SmartImportSession(models.Model):
    _name = 'smart.import.session'
    _description = 'Smart Import Session'
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('smart.import.session') or 'New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], default='draft', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    mapping_profile_id = fields.Many2one('smart.import.mapping.profile')
    options_json = fields.Text()
    stats_json = fields.Text()
    issues_json = fields.Text()
    log_text = fields.Text()
    error_csv_attachment_id = fields.Many2one('ir.attachment', string='Error CSV')
    file_line_ids = fields.One2many('smart.import.session.file', 'session_id', string='Files')

    stats_pretty = fields.Text(compute='_compute_pretty_json')
    issues_pretty = fields.Text(compute='_compute_pretty_json')

    @api.depends('stats_json', 'issues_json')
    def _compute_pretty_json(self):
        for session in self:
            session.stats_pretty = session._prettify_json(session.stats_json)
            session.issues_pretty = session._prettify_json(session.issues_json)

    def _prettify_json(self, json_text):
        if not json_text:
            return False
        try:
            return json.dumps(json.loads(json_text), indent=2, sort_keys=True)
        except Exception:
            return json_text

    def append_log(self, level, msg):
        self.ensure_one()
        line = f'[{fields.Datetime.now()}] {level}: {msg}'
        self.write({'log_text': f'{self.log_text or ""}{line}\n'})

    def set_stats(self, payload):
        self.ensure_one()
        self.stats_json = json.dumps(payload or {}, indent=2, sort_keys=True)

    def set_issues(self, payload):
        self.ensure_one()
        self.issues_json = json.dumps(payload or {}, indent=2, sort_keys=True)

    def make_error_csv(self, errors_list):
        self.ensure_one()
        output = io.StringIO()
        fieldnames = ['type', 'key', 'error']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for error in errors_list or []:
            writer.writerow({k: error.get(k, '') for k in fieldnames})
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.name}_errors.csv',
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue().encode('utf-8')),
            'mimetype': 'text/csv',
            'res_model': self._name,
            'res_id': self.id,
        })
        self.error_csv_attachment_id = attachment.id
        return attachment


class SmartImportSessionFile(models.Model):
    _name = 'smart.import.session.file'
    _description = 'Smart Import Session File'
    _order = 'id asc'

    session_id = fields.Many2one('smart.import.session', required=True, ondelete='cascade')
    attachment_id = fields.Many2one('ir.attachment', required=True, ondelete='cascade')
    filename = fields.Char(required=True)
    mimetype = fields.Char()
    kind = fields.Selection([('items', 'Items'), ('bom', 'BOM'), ('unknown', 'Unknown')], default='unknown', required=True)
    sheet_names_json = fields.Text()
    detected_sheets_json = fields.Text()
    header_row_json = fields.Text()
    preview_rows_json = fields.Text()
    detected_models_json = fields.Text()
    notes = fields.Text()
