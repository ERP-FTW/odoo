import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        leads._zip_assign_team_with_logging(trigger="create")
        return leads

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ("zip", "partner_id", "company_id", "country_id", "state_id", "phone", "email_from")):
            self._zip_assign_team_with_logging(trigger="write")
        return res

    # -------------------------
    # Helpers
    # -------------------------

    def _partner_sales_team_field_name(self):
        """Return the field name used on res.partner to store a sales team, if any."""
        partner_fields = self.env["res.partner"]._fields
        # If your module adds a real Many2one 'team_id' on partner, it will be here.
        if "team_id" in partner_fields:
            return "team_id"
        # Your DB: Studio field
        if "x_studio_sales_team" in partner_fields:
            return "x_studio_sales_team"
        return False

    def _get_partner_sales_team(self, partner):
        fname = self._partner_sales_team_field_name()
        return getattr(partner, fname) if (fname and partner) else False

    def _set_partner_sales_team(self, partner, team):
        fname = self._partner_sales_team_field_name()
        if not fname or not partner:
            return False
        try:
            # only write if different to reduce chatter/noise
            if getattr(partner, fname) != team:
                partner.write({fname: team.id})
            return True
        except Exception:
            _logger.exception(
                "[ZIP_ASSIGN][LEAD] Could not write partner field %s for partner=%s team=%s",
                fname, partner.id, team.id
            )
            return False

    # -------------------------
    # Main logic
    # -------------------------

    def _zip_assign_team_with_logging(self, trigger="manual"):
        """
        Assign crm.lead.team_id based on ZIP regex patterns (crm.team.zip_regex_ids).
        Also optionally sync the matched team to the partner's sales team field
        if one exists (team_id or x_studio_sales_team).
        """
        Team = self.env["crm.team"]

        for lead in self:
            partner = lead.partner_id
            company = lead.company_id or self.env.company

            if not partner:
                _logger.info(
                    "[ZIP_ASSIGN][LEAD][SKIP] lead=%s(%r) reason=no_partner_id trigger=%s",
                    lead.id, lead.name, trigger
                )
                continue

            zip_value = (partner.zip or lead.zip or "").strip()
            if not zip_value:
                _logger.info(
                    "[ZIP_ASSIGN][LEAD][SKIP] lead=%s(%r) partner=%s reason=missing_zip (partner.zip=%r lead.zip=%r) trigger=%s",
                    lead.id, lead.name, partner.id, partner.zip, lead.zip, trigger
                )
                continue

            # Candidate teams: only enabled ones
            teams = Team.search([("enable_zip_auto_assignment", "=", True)])
            _logger.info(
                "[ZIP_ASSIGN][LEAD] lead=%s partner=%s zip=%r candidates=%s trigger=%s",
                lead.id, partner.id, zip_value, len(teams), trigger
            )

            # Decide selected_team ONCE
            selected_team = False

            if not partner.company_id:
                # Partner has no company_id -> filter teams using lead/env company (NOT partner.company_id)
                _logger.info(
                    "[ZIP_ASSIGN][LEAD] lead=%s partner=%s note=partner_missing_company_id using_company=%s",
                    lead.id, partner.id, company.id
                )
                company_teams = teams.filtered(lambda t: (not t.company_id) or (t.company_id == company))
                _logger.info(
                    "[ZIP_ASSIGN][LEAD] lead=%s partner=%s eligible_after_company=%s",
                    lead.id, partner.id, len(company_teams)
                )
                selected_team = self._fallback_select_team_by_zip(zip_value, company_teams)
            else:
                # Partner has company_id -> safe to use partner selector (if present)
                if hasattr(partner, "_select_team_for_partner"):
                    selected_team = partner._select_team_for_partner(partner, teams)
                else:
                    selected_team = self._fallback_select_team_by_zip(zip_value, teams)

            if not selected_team:
                _logger.info(
                    "[ZIP_ASSIGN][LEAD][NO_MATCH] lead=%s partner=%s zip=%r trigger=%s",
                    lead.id, partner.id, zip_value, trigger
                )
                continue

            # Assign the LEAD TEAM (this is what controls pipeline assignment)
            if lead.team_id != selected_team:
                _logger.info(
                    "[ZIP_ASSIGN][LEAD][ASSIGN] lead=%s(%r) partner=%s zip=%r -> lead.team_id=%s(%s) trigger=%s",
                    lead.id, lead.name, partner.id, zip_value, selected_team.name, selected_team.id, trigger
                )
                lead.team_id = selected_team.id
            else:
                _logger.info(
                    "[ZIP_ASSIGN][LEAD][NOOP] lead=%s already team=%s(%s) trigger=%s",
                    lead.id,
                    lead.team_id.name if lead.team_id else None,
                    lead.team_id.id if lead.team_id else None,
                    trigger
                )

            # OPTIONAL: sync to partner "sales team" field if present (team_id or x_studio_sales_team)
            partner_team = self._get_partner_sales_team(partner)
            fname = self._partner_sales_team_field_name()
            if fname:
                if partner_team != selected_team:
                    _logger.info(
                        "[ZIP_ASSIGN][LEAD][PARTNER_SYNC] lead=%s partner=%s field=%s -> %s(%s)",
                        lead.id, partner.id, fname, selected_team.name, selected_team.id
                    )
                    self._set_partner_sales_team(partner, selected_team)
                else:
                    _logger.info(
                        "[ZIP_ASSIGN][LEAD][PARTNER_NOOP] lead=%s partner=%s field=%s already=%s(%s)",
                        lead.id, partner.id, fname, selected_team.name, selected_team.id
                    )
            else:
                _logger.info(
                    "[ZIP_ASSIGN][LEAD] lead=%s partner=%s note=no_partner_sales_team_field (no team_id / x_studio_sales_team)",
                    lead.id, partner.id
                )

        return True

    def _fallback_select_team_by_zip(self, zip_value, teams):
        """
        Minimal fallback if partner selector isn't available.
        Matches zip_value against team.zip_regex_ids patterns, chooses highest priority.
        """
        import re

        matching = self.env["crm.team"]
        for team in teams:
            patterns = team.zip_regex_ids.mapped("pattern") if team.zip_regex_ids else []
            for pat in patterns:
                try:
                    if re.match(pat, zip_value):
                        matching |= team
                        break
                except re.error:
                    _logger.exception(
                        "[ZIP_ASSIGN][LEAD][TEAM_SKIP] team=%s reason=invalid_regex pattern=%r",
                        team.id, pat
                    )
        if matching:
            matching = matching.sorted(key=lambda t: (-t.zip_assignment_priority, t.id))
            return matching[:1]
        return False