from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    email_extra_attachment = fields.Binary(
        string="Extra Email Attachment",
        attachment=True,
        help="This file will be auto-attached when emailing the invoice via the Send Invoice wizard."
    )
    email_extra_attachment_filename = fields.Char(
        string="Attachment Filename",
        help="Filename to use for the extra attachment."
    )

    def write(self, vals):
        res = super().write(vals)
        if "email_extra_attachment" in vals or "email_extra_attachment_filename" in vals:
            for move in self:
                _logger.info(
                    "EMAIL EXTRA ATTACHMENT write on move %s (id=%s): has_binary=%s filename=%s",
                    move.name, move.id,
                    bool(move.email_extra_attachment),
                    move.email_extra_attachment_filename,
                )
        return res
