from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    signup_block_duplicate_users = fields.Boolean(
        string="Enable duplicate user blocking",
        default=True,
        config_parameter="auth_signup_partner_link.block_duplicate_users",
    )
    signup_enable_partner_linking = fields.Boolean(
        string="Enable contact linking",
        default=True,
        config_parameter="auth_signup_partner_link.enable_partner_linking",
    )
    signup_partner_link_policy = fields.Selection(
        [
            ("never", "Never link automatically"),
            ("single_match", "Link when exactly one contact has this email and no user"),
            ("manual", "Require manual review"),
        ],
        string="Link signup to existing contact",
        default="single_match",
        config_parameter="auth_signup_partner_link.partner_link_policy",
    )
