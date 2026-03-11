from collections import defaultdict

from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    mail_issue_count = fields.Integer(compute="_compute_mail_issue_fields")
    mail_has_issue = fields.Boolean(compute="_compute_mail_issue_fields")
    mail_issue_text = fields.Char(compute="_compute_mail_issue_fields")
    mail_issue_message_id = fields.Many2one("mail.message", compute="_compute_mail_issue_fields")

    @api.depends("message_ids.notification_ids.notification_status", "message_ids.notification_ids.failure_reason", "message_ids.notification_ids.failure_type")
    def _compute_mail_issue_fields(self):
        failed_statuses = ("bounce", "exception")
        moves = self.filtered("id")
        notifs_by_move = defaultdict(lambda: self.env["mail.notification"])

        if moves:
            notifications = self.env["mail.notification"].sudo().search([
                ("mail_message_id.model", "=", "account.move"),
                ("mail_message_id.res_id", "in", moves.ids),
                ("notification_type", "=", "email"),
                ("notification_status", "in", failed_statuses),
            ])
            for notification in notifications:
                notifs_by_move[notification.mail_message_id.res_id] |= notification

        for move in self:
            move_notifications = notifs_by_move.get(move.id, self.env["mail.notification"])
            count = len(move_notifications)
            latest_notification = move_notifications.sorted(
                key=lambda n: (n.mail_message_id.date or fields.Datetime.now(), n.mail_message_id.id),
                reverse=True,
            )[:1]
            latest_notification = latest_notification and latest_notification[0] or self.env["mail.notification"]

            reason = ""
            if latest_notification:
                reason = self._get_mail_issue_reason(latest_notification)

            move.mail_issue_count = count
            move.mail_has_issue = bool(count)
            move.mail_issue_message_id = latest_notification.mail_message_id if latest_notification else False
            move.mail_issue_text = self._build_mail_issue_text(count=count, reason=reason)

    def _get_mail_issue_reason(self, notification):
        reason = (notification.failure_reason or "").strip()
        if not reason and notification.failure_type:
            reason = dict(notification._fields["failure_type"].selection).get(notification.failure_type, "")
        if not reason:
            return ""

        first_line = reason.splitlines()[0].strip()
        return first_line[:120]

    def _build_mail_issue_text(self, count, reason=""):
        if not count:
            return False
        if count == 1 and reason:
            return _("Email delivery issue detected: %(reason)s.", reason=reason)
        if count > 1:
            return _("Email delivery issue detected for %(count)s recipients.", count=count)
        return _("Email delivery issue detected.")

    def action_open_email_issues(self):
        self.ensure_one()
        self = self.with_context(active_test=False)
        message_ids = self.env["mail.message"].sudo().search([
            ("model", "=", "account.move"),
            ("res_id", "=", self.id),
        ]).ids

        return {
            "type": "ir.actions.act_window",
            "name": _("Email Issues"),
            "res_model": "mail.notification",
            "view_mode": "list,form",
            "domain": [
                ("mail_message_id", "in", message_ids or [0]),
                ("notification_type", "=", "email"),
                ("notification_status", "in", ("bounce", "exception")),
            ],
            "context": {
                "search_default_notification_type": "email",
                "default_notification_type": "email",
            },
        }
