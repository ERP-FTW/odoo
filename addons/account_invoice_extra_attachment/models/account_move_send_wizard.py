from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    @api.depends(
        "mail_template_id",
        "sending_methods",
        "invoice_edi_format",
        "extra_edis",
        "move_id",
    )
    def _compute_mail_attachments_widget(self):
        # Let Odoo build the default attachments first (invoice PDF, EDI, etc.)
        super()._compute_mail_attachments_widget()

        Attachment = self.env["ir.attachment"]

        for wizard in self:
            move = wizard.move_id
            if not move:
                _logger.debug(
                    "Extra attachment: wizard %s has no move_id, skipping",
                    wizard.id,
                )
                continue

            if not move.email_extra_attachment:
                _logger.debug(
                    "Extra attachment: move %s has no email_extra_attachment",
                    move.id,
                )
                continue

            extra_attachment = Attachment.search([
                ("res_model", "=", "account.move"),
                ("res_id", "=", move.id),
                ("res_field", "=", "email_extra_attachment"),
            ], limit=1)

            if not extra_attachment:
                _logger.warning(
                    "Extra attachment: binary set on move %s but no ir.attachment found",
                    move.id,
                )
                continue

            widget_data = list(wizard.mail_attachments_widget or [])

            # Guardrail: avoid duplicates
            if any(a.get("id") == extra_attachment.id for a in widget_data):
                _logger.debug(
                    "Extra attachment: attachment %s already present for move %s",
                    extra_attachment.id, move.id,
                )
                continue

            widget_data.append({
                "id": extra_attachment.id,
                "name": extra_attachment.name
                        or move.email_extra_attachment_filename
                        or "attachment",
                "mimetype": extra_attachment.mimetype
                            or "application/octet-stream",
                "checksum": extra_attachment.checksum,
            })

            wizard.mail_attachments_widget = widget_data

            _logger.info(
                "Extra attachment: attached ir.attachment %s to email for move %s",
                extra_attachment.id, move.id,
            )
