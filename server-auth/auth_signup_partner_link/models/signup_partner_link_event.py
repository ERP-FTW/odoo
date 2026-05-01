from odoo import fields, models


class SignupPartnerLinkEvent(models.Model):
    _name = "auth.signup.partner.link.event"
    _description = "Signup Partner Link Event"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    email = fields.Char(required=True, index=True, tracking=True)
    event_type = fields.Selection(
        [
            ("existing_user_blocked", "Existing User Blocked"),
            ("existing_user_found_not_blocked", "Existing User Found Not Blocked"),
            ("partner_linked", "Partner Linked"),
            ("partner_match_linking_disabled", "Partner Match Linking Disabled"),
            ("partner_manual_review", "Partner Manual Review"),
            ("partner_multiple_conflict", "Partner Multiple Conflict"),
            ("partner_has_existing_user", "Partner Has Existing User"),
            ("signup_created_new_partner", "Signup Created New Partner"),
            ("signup_error", "Signup Error"),
        ],
        required=True,
        index=True,
        tracking=True,
    )
    state = fields.Selection(
        [("open", "Open"), ("reviewed", "Reviewed"), ("resolved", "Resolved"), ("ignored", "Ignored")],
        default="open",
        index=True,
        tracking=True,
    )
    message = fields.Text()
    user_id = fields.Many2one("res.users")
    partner_id = fields.Many2one("res.partner")
    partner_ids = fields.Many2many("res.partner")
    request_ip = fields.Char()
    user_agent = fields.Char()
    signup_policy = fields.Char()
    duplicate_blocking_enabled = fields.Boolean()
    partner_linking_enabled = fields.Boolean()
