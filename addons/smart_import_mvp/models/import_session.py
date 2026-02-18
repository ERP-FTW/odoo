import json

from odoo import api, fields, models


class FulcrumImportSession(models.Model):
    _name = 'mlr.fulcrum.import.session'
    _description = 'Fulcrum Import Session'
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('mlr.fulcrum.import.session') or 'New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], default='draft', required=True)
    items_attachment_id = fields.Many2one('ir.attachment', string='Items Attachment')
    bom_attachment_ids = fields.Many2many('ir.attachment', 'mlr_fulcrum_session_ir_attachment_rel', 'session_id', 'attachment_id', string='BOM Attachments')
    log_text = fields.Text(readonly=True)
    stats_json = fields.Text(readonly=True)
    issues_json = fields.Text(readonly=True)
    error_csv_attachment_id = fields.Many2one('ir.attachment', string='Error CSV')

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

    def append_log(self, message, level='INFO'):
        self.ensure_one()
        line = f'[{fields.Datetime.now()}] {level}: {message}'
        self.write({'log_text': f'{self.log_text or ""}{line}\n'})
