import logging

from odoo import _, http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

_logger = logging.getLogger(__name__)


class AuthSignupPartnerLinkHome(AuthSignupHome):
    @http.route()
    def web_auth_signup(self, *args, **kw):
        if request.httprequest.method == "POST":
            service = request.env["auth.signup.partner.link.service"].sudo().with_context(
                signup_request={
                    "ip": request.httprequest.remote_addr,
                    "user_agent": request.httprequest.user_agent.string,
                }
            )
            try:
                decision = service.resolve_signup(request.params.get("login"))
                if decision["action"] == "block":
                    qcontext = self.get_auth_signup_qcontext()
                    qcontext["error"] = decision["error"]
                    return request.render("auth_signup.signup", qcontext)
                if decision["action"] == "link_partner" and decision.get("partner"):
                    request.params["partner_id"] = decision["partner"].id
                    if not request.params.get("name"):
                        request.params["name"] = decision["partner"].name
            except Exception:
                _logger.exception("[Signup Partner Link] Exception during signup identity resolution")
                config = service._get_signup_config()
                service._create_event(
                    service._normalize_email(request.params.get("login")),
                    "signup_error",
                    _("Unhandled exception while resolving signup identity."),
                    config,
                )
        return super().web_auth_signup(*args, **kw)

    def _prepare_signup_values(self, qcontext):
        values = super()._prepare_signup_values(qcontext)
        if qcontext.get("partner_id"):
            values["partner_id"] = int(qcontext["partner_id"])
        values["email"] = qcontext.get("email") or qcontext.get("login")
        return values
