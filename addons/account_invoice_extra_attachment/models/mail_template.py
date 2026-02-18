from odoo import models
import logging

_logger = logging.getLogger(__name__)

class MailTemplate(models.Model):
    _inherit = "mail.template"

    def generate_email(self, res_ids, fields=None):
        """Extend core generate_email to append the extra invoice attachment.

        This is template-based, so it works whether you send from:
        - the Send & Print / Send Invoice wizard
        - chatter (Send message with the invoice template)
        - mass-mailing using the invoice template

        It never removes existing attachments; it simply appends one more
        ir.attachment if `email_extra_attachment` is set on the invoice.
        """
        emails = super().generate_email(res_ids, fields=fields)

        if self.model != "account.move":
            # Not an invoice-related template; nothing to do.
            return emails

        Attachment = self.env["ir.attachment"]

        # If you want to restrict to a specific invoice template, uncomment:
        # invoice_tmpl = self.env.ref("account.email_template_edi_invoice", raise_if_not_found=False)
        # if not invoice_tmpl or self.id != invoice_tmpl.id:
        #     return emails

        for res_id, values in emails.items():
            move = self.env["account.move"].browse(res_id)
            if not move or not move.email_extra_attachment:
                _logger.info(
                    "EMAIL EXTRA ATTACHMENT (v4): move id=%s has no extra attachment, skipping",
                    res_id,
                )
                continue

            # Try to reuse the attachment that backs the Binary field, if present
            extra_attachment = Attachment.search([
                ("res_model", "=", "account.move"),
                ("res_id", "=", move.id),
                ("res_field", "=", "email_extra_attachment"),
            ], limit=1)

            if not extra_attachment:
                # As a fallback, explicitly create an attachment from the binary
                _logger.info(
                    "EMAIL EXTRA ATTACHMENT (v4): no backing ir.attachment found for move id=%s, creating one",
                    move.id,
                )
                extra_attachment = Attachment.create({
                    "name": move.email_extra_attachment_filename or "attachment",
                    "res_model": "account.move",
                    "res_id": move.id,
                    "type": "binary",
                    "datas": move.email_extra_attachment,
                    "mimetype": "application/octet-stream",
                })
            else:
                _logger.info(
                    "EMAIL EXTRA ATTACHMENT (v4): reusing backing ir.attachment id=%s for move id=%s",
                    extra_attachment.id, move.id,
                )

            # Ensure we have a list of attachment_ids
            attachment_ids = list(values.get("attachment_ids") or [])
            if extra_attachment.id in attachment_ids:
                _logger.info(
                    "EMAIL EXTRA ATTACHMENT (v4): attachment id=%s already in attachment_ids for move id=%s, skipping",
                    extra_attachment.id, move.id,
                )
                continue

            attachment_ids.append(extra_attachment.id)
            values["attachment_ids"] = attachment_ids

            _logger.info(
                "EMAIL EXTRA ATTACHMENT (v4): appended attachment id=%s to email for move id=%s; attachment_ids=%s",
                extra_attachment.id, move.id, attachment_ids,
            )

        return emails
