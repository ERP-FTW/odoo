import ast
import logging
import re

from odoo import api, fields, models
from odoo.tools import ustr

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    exclude_from_zip_assign = fields.Boolean(
        string="Exclude from ZIP Assignment",
        default=False,
        help="If checked, this partner will not be automatically assigned "
        "to a CRM team based on ZIP code patterns.",
    )


    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        company_dependent=True,
        index=True,
        help="Sales team assigned to this contact (used for ZIP-based routing).",
    )
    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._process_zip_assignment()
        return partners

    def write(self, vals):
        result = super().write(vals)
        # broaden triggers a bit so we can debug without guessing
        if any(k in vals for k in ("zip", "company_id", "exclude_from_zip_assign", "country_id", "state_id", "type")):
            self._process_zip_assignment()
        return result

    def _log_partner_skip(self, partner, reasons):
        _logger.info(
            "[ZIP_ASSIGN][PARTNER][SKIP] id=%s name=%r reasons=%s zip=%r company_id=%s country=%s state=%s type=%s excluded=%s",
            partner.id, partner.name, ",".join(reasons),
            partner.zip, partner.company_id.id if partner.company_id else None,
            partner.country_id.code if partner.country_id else None,
            partner.state_id.code if partner.state_id else None,
            partner.type,
            bool(partner.exclude_from_zip_assign),
        )

    def _process_zip_assignment(self):
        """
        Assign partner.team_id based on ZIP patterns.
        Logging is intentionally verbose so we can see why it didn't trigger.
        """
        for partner in self:
            reasons = []
            if not (partner.zip or "").strip():
                reasons.append("missing_zip")
            if partner.exclude_from_zip_assign:
                reasons.append("excluded")
            # keep company_id required (multi-company safety), but log it
            if reasons:
                self._log_partner_skip(partner, reasons)
                continue

            # choose routing company even if partner.company_id is empty
            routing_company = partner.company_id or self.env.company

            teams = self.env["crm.team"].search([("enable_zip_auto_assignment", "=", True)])
            _logger.info(
                "[ZIP_ASSIGN][PARTNER] id=%s name=%r zip=%r candidates=%s",
                partner.id, partner.name, partner.zip, len(teams)
            )

            selected_team = self._select_team_for_partner(partner, teams)
            if not selected_team:
                _logger.info(
                    "[ZIP_ASSIGN][PARTNER][NO_MATCH] id=%s name=%r zip=%r",
                    partner.id, partner.name, partner.zip
                )
                continue

            _logger.info(
                "[ZIP_ASSIGN][PARTNER][ASSIGN] id=%s name=%r zip=%r -> team=%s(%s)",
                partner.id, partner.name, partner.zip, selected_team.name, selected_team.id
            )
            partner.team_id = selected_team.id

        return True

    def _select_team_for_partner(self, partner, teams):
        """
        RELAXED filtering:
        - Company must match (required)
        - If team.country_ids is set AND partner.country_id is set -> must match
        - If team.state_ids is set AND partner.state_id is set -> must match
        - If partner has no country/state, don't discard; match by ZIP only
        """
        # company match only
        routing_company = partner.company_id or self.env.company
        eligible = teams.filtered(lambda t: (not t.company_id) or (t.company_id == routing_company))
        _logger.info(
            "[ZIP_ASSIGN][PARTNER] id=%s eligible_after_company=%s",
            partner.id, len(eligible)
        )

        matching = self.env["crm.team"]
        zip_value = (partner.zip or "").strip()

        for team in eligible:
            # optional geographic filters
            if team.country_ids and partner.country_id and partner.country_id not in team.country_ids:
                _logger.info("[ZIP_ASSIGN][PARTNER][TEAM_SKIP] partner=%s team=%s reason=country_mismatch", partner.id, team.id)
                continue
            if team.state_ids and partner.state_id and partner.state_id not in team.state_ids:
                _logger.info("[ZIP_ASSIGN][PARTNER][TEAM_SKIP] partner=%s team=%s reason=state_mismatch", partner.id, team.id)
                continue

            # pre-condition domain (guarded)
            domain_match = True
            if team.pre_zip_match_condition:
                try:
                    partner_domain = ast.literal_eval(ustr(team.pre_zip_match_condition))
                    domain_match = bool(partner.filtered_domain(partner_domain))
                except Exception as e:
                    domain_match = False
                    _logger.exception(
                        "[ZIP_ASSIGN][PARTNER][TEAM_SKIP] partner=%s team=%s reason=bad_pre_condition error=%s",
                        partner.id, team.id, e
                    )
            if not domain_match:
                _logger.info("[ZIP_ASSIGN][PARTNER][TEAM_SKIP] partner=%s team=%s reason=pre_condition_false", partner.id, team.id)
                continue

            # zip regex match
            patterns = team.zip_regex_ids.mapped("pattern") if team.zip_regex_ids else []
            if not patterns:
                _logger.info("[ZIP_ASSIGN][PARTNER][TEAM_SKIP] partner=%s team=%s reason=no_patterns", partner.id, team.id)
                continue

            matched = False
            for pat in patterns:
                try:
                    if re.match(pat, zip_value):
                        _logger.info(
                            "[ZIP_ASSIGN][PARTNER][TEAM_MATCH] partner=%s team=%s zip=%r pattern=%r",
                            partner.id, team.id, zip_value, pat
                        )
                        matched = True
                        break
                except re.error:
                    _logger.exception(
                        "[ZIP_ASSIGN][PARTNER][TEAM_SKIP] partner=%s team=%s reason=invalid_regex pattern=%r",
                        partner.id, team.id, pat
                    )

            if matched:
                matching |= team

        if matching:
            matching = matching.sorted(key=lambda t: (-t.zip_assignment_priority, t.id))
            chosen = matching[:1]
            _logger.info(
                "[ZIP_ASSIGN][PARTNER] id=%s matched_teams=%s chosen=%s(%s)",
                partner.id,
                ",".join(str(t.id) for t in matching),
                chosen.name, chosen.id
            )
            return chosen
        return False