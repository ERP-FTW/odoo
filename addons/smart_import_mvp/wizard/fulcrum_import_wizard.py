import json

from odoo import _, fields, models
from odoo.exceptions import UserError


class FulcrumImportWizard(models.TransientModel):
    _name = 'mlr.fulcrum.import.wizard'
    _description = 'Fulcrum Import Wizard'

    step = fields.Selection([('upload', 'Upload/Options'), ('plan', 'Plan/Run')], default='upload', required=True)

    items_file = fields.Binary(required=True)
    items_filename = fields.Char()
    bom_line_ids = fields.One2many('mlr.fulcrum.import.wizard.bom.line', 'wizard_id', string='BOM Files')

    auto_create_unknown_uom = fields.Boolean(default=True)
    create_locations_putaway = fields.Boolean(default=True)
    create_placeholder_missing_bom_children = fields.Boolean(default=False)
    orderpoint_max_policy = fields.Selection([('same_as_min', 'Same as Min'), ('double_min', 'Double Min')], default='same_as_min', required=True)
    force_buy_route = fields.Boolean(default=False)
    force_manufacture_route = fields.Boolean(default=False)
    force_purchase_ok = fields.Boolean(default=False)
    mapping_profile_id = fields.Many2one(
        'smart.import.mapping.profile',
        string='Mapping Profile',
        default=lambda self: self._default_mapping_profile_id(),
        domain="[('active', '=', True)]",
    )

    session_id = fields.Many2one('mlr.fulcrum.import.session', readonly=True)
    plan_text = fields.Text(readonly=True)
    issues_text = fields.Text(readonly=True)
    route_preview_counts_text = fields.Text(readonly=True)
    sample_preview_line_ids = fields.One2many('mlr.fulcrum.import.wizard.preview.line', 'wizard_id', readonly=True)

    def _default_mapping_profile_id(self):
        company = self.env.company
        profile = self.env['smart.import.mapping.profile'].search([
            ('name', '=', 'Fulcrum Default'),
            ('active', '=', True),
            ('company_id', '=', company.id),
        ], limit=1)
        if not profile:
            profile = self.env['smart.import.mapping.profile'].search([
                ('name', '=', 'Fulcrum Default'),
                ('active', '=', True),
                ('company_id', '=', False),
            ], limit=1)
        if not profile:
            profile = self.env['smart.import.mapping.profile'].search([
                ('active', '=', True),
                '|', ('company_id', '=', company.id), ('company_id', '=', False),
            ], limit=1)
        if not profile:
            profile = self.env['smart.import.mapping.profile'].search([('active', '=', True)], limit=1)
        return profile

    def _prepare_attachment(self, name, file_data, session):
        return self.env['ir.attachment'].create({
            'name': name,
            'datas': file_data,
            'type': 'binary',
            'res_model': session._name,
            'res_id': session.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

    def _open_self(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fulcrum Import Wizard'),
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    def action_generate_plan(self):
        self.ensure_one()
        if not self.items_file:
            raise UserError(_('Please upload an items file.'))
        engine = self.env['mlr.fulcrum.import.engine']

        session = self.session_id or self.env['mlr.fulcrum.import.session'].create({})
        if self.session_id:
            session.write({'error_csv_attachment_id': False})

        items_attachment = self._prepare_attachment(self.items_filename or 'items.xlsx', self.items_file, session)
        bom_attachments = self.env['ir.attachment']
        for line in self.bom_line_ids:
            if not line.file_data:
                continue
            bom_attachments |= self._prepare_attachment(line.filename or 'bom.xlsx', line.file_data, session)

        session.write({
            'items_attachment_id': items_attachment.id,
            'bom_attachment_ids': [(6, 0, bom_attachments.ids)],
            'state': 'draft',
            'log_text': False,
            'stats_json': False,
            'issues_json': False,
        })

        items_rows = engine.parse_items_xlsx(items_attachment, mapping_profile=self.mapping_profile_id)
        bom_rows = []
        for attachment in bom_attachments:
            bom_rows.extend(engine.parse_bom_xlsx(attachment))

        plan = engine.build_plan(
            items_rows,
            bom_rows,
            mapping_profile=self.mapping_profile_id,
            options={
                'orderpoint_max_policy': self.orderpoint_max_policy,
                'force_buy_route': self.force_buy_route,
                'force_manufacture_route': self.force_manufacture_route,
                'force_purchase_ok': self.force_purchase_ok,
            },
        )
        session.write({
            'stats_json': json.dumps({
                'counts': plan['counts'],
                'proposed_defaults': plan['proposed_defaults'],
                'route_preview_counts': plan['route_preview_counts'],
                'sample_previews': plan['sample_previews'],
            }, indent=2, sort_keys=True),
            'issues_json': json.dumps(plan['issues'], indent=2, sort_keys=True),
            'state': 'planned',
        })
        session.append_log(_('Plan generated: %s items rows, %s bom lines') % (len(items_rows), len(bom_rows)))

        self.sample_preview_line_ids.unlink()
        line_commands = []
        for sample in plan['sample_previews']:
            line_commands.append((0, 0, {
                'default_code': sample.get('default_code'),
                'name': sample.get('name'),
                'buy_or_make': sample.get('buy_or_make'),
                'proposed_purchase_ok': sample.get('purchase_ok'),
                'proposed_routes': ', '.join(sample.get('routes', [])),
            }))

        self.write({
            'session_id': session.id,
            'plan_text': json.dumps(
                {
                    'steps': plan['steps'],
                    'counts': plan['counts'],
                    'mapped_fields': plan['mapped_fields'],
                    'proposed_defaults': plan['proposed_defaults'],
                },
                indent=2,
                sort_keys=True,
            ),
            'issues_text': json.dumps(plan['issues'], indent=2, sort_keys=True),
            'route_preview_counts_text': json.dumps(plan['route_preview_counts'], indent=2, sort_keys=True),
            'sample_preview_line_ids': line_commands,
            'step': 'plan',
        })
        return self._open_self()

    def _run_execution(self, dry_run=False):
        self.ensure_one()
        if not self.session_id or not self.session_id.items_attachment_id:
            raise UserError(_('Generate a plan first.'))

        engine = self.env['mlr.fulcrum.import.engine']
        items_rows = engine.parse_items_xlsx(self.session_id.items_attachment_id, mapping_profile=self.mapping_profile_id)
        bom_rows = []
        for attachment in self.session_id.bom_attachment_ids:
            bom_rows.extend(engine.parse_bom_xlsx(attachment))

        result = engine.execute(
            self.session_id,
            items_rows,
            bom_rows,
            {
                'auto_create_unknown_uom': self.auto_create_unknown_uom,
                'create_locations_putaway': self.create_locations_putaway,
                'create_placeholder_missing_bom_children': self.create_placeholder_missing_bom_children,
                'orderpoint_max_policy': self.orderpoint_max_policy,
                'mapping_profile_id': self.mapping_profile_id.id,
                'force_buy_route': self.force_buy_route,
                'force_manufacture_route': self.force_manufacture_route,
                'force_purchase_ok': self.force_purchase_ok,
            },
            dry_run=dry_run,
        )
        self.write({
            'plan_text': json.dumps(result['stats'], indent=2, sort_keys=True),
            'issues_text': json.dumps(result['issues'], indent=2, sort_keys=True),
            'step': 'plan',
        })
        return self._open_self()

    def action_dry_run(self):
        return self._run_execution(dry_run=True)

    def action_approve_import(self):
        return self._run_execution(dry_run=False)


class FulcrumImportWizardBomLine(models.TransientModel):
    _name = 'mlr.fulcrum.import.wizard.bom.line'
    _description = 'Fulcrum Import Wizard BOM File'

    wizard_id = fields.Many2one('mlr.fulcrum.import.wizard', required=True, ondelete='cascade')
    file_data = fields.Binary(required=True)
    filename = fields.Char(required=True)


class FulcrumImportWizardPreviewLine(models.TransientModel):
    _name = 'mlr.fulcrum.import.wizard.preview.line'
    _description = 'Fulcrum Import Wizard Preview Line'

    wizard_id = fields.Many2one('mlr.fulcrum.import.wizard', required=True, ondelete='cascade')
    default_code = fields.Char(readonly=True)
    name = fields.Char(readonly=True)
    buy_or_make = fields.Char(readonly=True)
    proposed_purchase_ok = fields.Boolean(readonly=True)
    proposed_routes = fields.Char(readonly=True)
