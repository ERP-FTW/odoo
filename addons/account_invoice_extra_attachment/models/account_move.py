import logging
import mimetypes

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # Deprecated legacy fields (kept for backward compatibility / migration).
    email_extra_attachment = fields.Binary(
        string="Extra Email Attachment (Legacy)",
        attachment=True,
        help="Deprecated: migrated into Extra Email Attachments.",
    )
    email_extra_attachment_filename = fields.Char(
        string="Attachment Filename (Legacy)",
        help="Deprecated: migrated into Extra Email Attachments.",
    )
    email_extra_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Extra Email Attachments",
        domain="[('res_model', '=', 'account.move'), ('res_id', '=', id)]",
        help="Files added here are automatically attached when emailing the invoice.",
    )

    def _get_legacy_extra_attachment_filename(self):
        self.ensure_one()
        filename = (self.email_extra_attachment_filename or "").strip()
        if filename:
            return filename
        return f"invoice_{self.id or 'attachment'}.bin"

    def _migrate_legacy_extra_attachment_to_m2m(self):
        """Create an ir.attachment from legacy Binary field and link it to M2M."""
        Attachment = self.env["ir.attachment"]
        for move in self:
            if not move.id or not move.email_extra_attachment:
                continue

            existing = move.email_extra_attachment_ids.filtered(
                lambda att: att.res_model == "account.move"
                and att.res_id == move.id
                and att.res_field == "email_extra_attachment"
            )
            if existing:
                _logger.debug(
                    "Legacy extra attachment already migrated for move %s with attachment %s",
                    move.id,
                    existing.ids,
                )
                continue

            filename = move._get_legacy_extra_attachment_filename()
            guessed_mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"

            attachment_vals = {
                "name": filename,
                "res_model": "account.move",
                "res_id": move.id,
                "res_field": "email_extra_attachment",
                "type": "binary",
                "datas": move.email_extra_attachment,
                "mimetype": guessed_mimetype,
            }
            created_attachment = Attachment.create(attachment_vals)
            move.email_extra_attachment_ids = [(4, created_attachment.id)]

            _logger.info(
                "Migrated legacy extra attachment on move %s to ir.attachment %s (%s, %s)",
                move.id,
                created_attachment.id,
                filename,
                guessed_mimetype,
            )

    def action_migrate_legacy_extra_attachment(self):
        """Helper action for server actions / manual migrations."""
        self._migrate_legacy_extra_attachment_to_m2m()
        return True
