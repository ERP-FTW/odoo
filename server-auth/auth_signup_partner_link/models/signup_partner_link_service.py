import logging

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class SignupPartnerLinkService(models.AbstractModel):
    _name = "auth.signup.partner.link.service"
    _description = "Signup Partner Link Service"

    @api.model
    def _normalize_email(self, email):
        return (email or "").strip().lower()

    @api.model
    def _get_signup_config(self):
        icp = self.env["ir.config_parameter"].sudo()
        block_raw = icp.get_param("auth_signup_partner_link.block_duplicate_users")
        link_raw = icp.get_param("auth_signup_partner_link.enable_partner_linking")
        policy = icp.get_param("auth_signup_partner_link.partner_link_policy") or "single_match"
        if policy not in {"never", "single_match", "manual"}:
            policy = "single_match"
        return {
            "block_duplicate_users": False if block_raw == "False" else True,
            "enable_partner_linking": False if link_raw == "False" else True,
            "partner_link_policy": policy,
        }

    @api.model
    def _create_event(self, email, event_type, message, config, partner=False, partners=False, user=False):
        req = self.env.context.get("signup_request") or {}
        vals = {
            "name": f"Signup event: {event_type}",
            "email": email,
            "event_type": event_type,
            "message": message,
            "user_id": user.id if user else False,
            "partner_id": partner.id if partner else False,
            "partner_ids": [(6, 0, partners.ids)] if partners else False,
            "request_ip": req.get("ip"),
            "user_agent": req.get("user_agent"),
            "signup_policy": config["partner_link_policy"],
            "duplicate_blocking_enabled": config["block_duplicate_users"],
            "partner_linking_enabled": config["enable_partner_linking"],
        }
        event = self.env["auth.signup.partner.link.event"].sudo().create(vals)
        event.message_post(body=message)
        return event

    @api.model
    def resolve_signup(self, login):
        email = self._normalize_email(login)
        config = self._get_signup_config()
        _logger.info("[Signup Partner Link] normalized_email=%s", email)
        _logger.info("[Signup Partner Link] config=%s", config)
        if not email:
            return {"action": "continue", "email": email, "partner": False}

        users = self.env["res.users"].sudo().search(["|", ("login", "=ilike", email), ("email", "=ilike", email)])
        _logger.info("[Signup Partner Link] existing_user_ids=%s", users.ids)
        if users and config["block_duplicate_users"]:
            msg = _("Signup blocked because an existing user already uses this email/login.")
            self._create_event(email, "existing_user_blocked", msg, config, user=users[0])
            return {
                "action": "block",
                "error": _("An account already exists for this email address. Please log in or reset your password."),
                "email": email,
            }
        if users:
            self._create_event(
                email,
                "existing_user_found_not_blocked",
                _("Matching user found but duplicate blocking is disabled."),
                config,
                user=users[0],
            )

        partners = self.env["res.partner"].sudo().search([("email", "=ilike", email)])
        _logger.info("[Signup Partner Link] matching_partner_ids=%s count=%s", partners.ids, len(partners))
        if not config["enable_partner_linking"]:
            if partners:
                self._create_event(
                    email,
                    "partner_match_linking_disabled",
                    _("Matching contact found but contact linking is disabled."),
                    config,
                    partners=partners,
                )
            return {"action": "continue", "email": email, "partner": False}

        policy = config["partner_link_policy"]
        if policy == "never":
            if partners:
                self._create_event(
                    email,
                    "partner_match_linking_disabled",
                    _("Matching contact found but policy is set to never link automatically."),
                    config,
                    partners=partners,
                )
            return {"action": "continue", "email": email, "partner": False}

        if policy == "manual" and partners:
            _logger.warning("[Signup Partner Link] manual review required for email=%s", email)
            self._create_event(
                email,
                "partner_manual_review",
                _("Signup blocked for manual review because contact(s) match this email."),
                config,
                partner=partners[:1],
                partners=partners,
            )
            return {"action": "block", "error": _("Your email matches an existing contact. Please contact us so we can connect your account correctly."), "email": email}

        if policy == "single_match":
            if len(partners) > 1:
                _logger.warning("[Signup Partner Link] multiple partner conflict for email=%s", email)
                self._create_event(
                    email,
                    "partner_multiple_conflict",
                    _("Signup conflict: multiple contacts matched this email. No user was created."),
                    config,
                    partners=partners,
                )
                return {"action": "block", "error": _("We found more than one contact with this email address. Please contact us so we can connect your account correctly."), "email": email}
            if len(partners) == 1:
                partner = partners[0]
                if partner.user_ids:
                    self._create_event(
                        email,
                        "partner_has_existing_user",
                        _("Signup blocked because matching contact already has a linked user."),
                        config,
                        partner=partner,
                        user=partner.user_ids[0],
                    )
                    return {"action": "block", "error": _("An account already exists for this email address. Please log in or reset your password."), "email": email}
                _logger.info("[Signup Partner Link] partner linked partner_id=%s", partner.id)
                self._create_event(email, "partner_linked", _("Portal signup linked existing contact to new user."), config, partner=partner)
                partner.message_post(body=_("Portal signup linked this existing contact to a new user for email %s.") % email)
                return {"action": "link_partner", "partner": partner, "email": email}

        _logger.info("[Signup Partner Link] normal signup allowed email=%s", email)
        return {"action": "continue", "email": email, "partner": False}
