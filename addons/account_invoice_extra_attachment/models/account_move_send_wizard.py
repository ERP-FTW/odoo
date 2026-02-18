import logging

from odoo import api, models

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

        for wizard in self:
            move = wizard.move_id
            if not move:
                _logger.debug("Extra attachments: wizard %s has no move_id, skipping", wizard.id)
                continue

            # Safe migration entry point on user interaction, not on every write.
            move._migrate_legacy_extra_attachment_to_m2m()

            widget_data = list(wizard.mail_attachments_widget or [])
            widget_attachment_ids = {data.get("id") for data in widget_data if data.get("id")}

            for extra_attachment in move.email_extra_attachment_ids.filtered(
                lambda att: att.res_model == "account.move" and att.res_id == move.id
            ):
                if extra_attachment.id in widget_attachment_ids:
                    continue

                widget_data.append(
                    {
                        "id": extra_attachment.id,
                        "name": extra_attachment.name or "attachment",
                        "mimetype": extra_attachment.mimetype or "application/octet-stream",
                        "checksum": extra_attachment.checksum,
                    }
                )
                widget_attachment_ids.add(extra_attachment.id)

            wizard.mail_attachments_widget = widget_data
            _logger.info(
                "Extra attachments: prepared %s extra attachment(s) for move %s in send wizard",
                len(move.email_extra_attachment_ids),
                move.id,
            )
