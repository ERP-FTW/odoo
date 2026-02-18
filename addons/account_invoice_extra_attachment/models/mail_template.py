import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def generate_email(self, res_ids, fields=None):
        """Extend core generate_email to append invoice extra attachments."""
        emails = super().generate_email(res_ids, fields=fields)

        if self.model != "account.move":
            return emails

        moves = self.env["account.move"].browse(res_ids)
        moves._migrate_legacy_extra_attachment_to_m2m()

        for res_id, values in emails.items():
            move = self.env["account.move"].browse(res_id)
            if not move:
                continue

            attachment_ids = list(values.get("attachment_ids") or [])
            for attachment in move.email_extra_attachment_ids.filtered(
                lambda att: att.res_model == "account.move" and att.res_id == move.id
            ):
                if attachment.id not in attachment_ids:
                    attachment_ids.append(attachment.id)

            values["attachment_ids"] = attachment_ids
            _logger.info(
                "Extra attachments: template email for move %s includes %s extra attachment(s)",
                move.id,
                len(move.email_extra_attachment_ids),
            )

        return emails
