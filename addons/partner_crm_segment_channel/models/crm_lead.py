from odoo import api, fields, models

from .selection_values import CHANNEL_SELECTION, SEGMENT_SELECTION


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    segment = fields.Selection(
        selection=SEGMENT_SELECTION,
        string='Core Segment',
        index=True,
    )
    channel = fields.Selection(
        selection=CHANNEL_SELECTION,
        string='Sales Channel',
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        partners = self.env['res.partner'].browse([
            vals['partner_id'] for vals in vals_list if vals.get('partner_id')
        ])
        partners_by_id = {partner.id: partner for partner in partners}
        for vals in vals_list:
            self._prefill_segment_channel_from_partner_vals(vals, partners_by_id=partners_by_id)
        leads = super().create(vals_list)
        leads._sync_segment_channel_to_partner()
        return leads

    def write(self, vals):
        if 'partner_id' in vals:
            for lead in self:
                lead_vals = dict(vals)
                lead._prefill_segment_channel_from_partner_vals(lead_vals, lead=lead)
                super(CrmLead, lead).write(lead_vals)
            self._sync_segment_channel_to_partner()
            return True

        result = super().write(vals)
        if any(field_name in vals for field_name in ('segment', 'channel')):
            self._sync_segment_channel_to_partner()
        return result

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        values = super()._prepare_customer_values(partner_name, is_company=is_company, parent_id=parent_id)
        values.update({
            'segment': self.segment,
            'channel': self.channel,
        })
        return values

    def _handle_partner_assignment(self, force_partner_id=False, create_missing=True):
        result = super()._handle_partner_assignment(force_partner_id=force_partner_id, create_missing=create_missing)
        self._sync_segment_channel_to_partner()
        return result

    @staticmethod
    def _prefill_segment_channel_from_partner_vals(vals, lead=None, partners_by_id=None):
        partner_id = vals.get('partner_id')
        if not partner_id:
            return

        partner = lead.env['res.partner'].browse(partner_id) if lead else partners_by_id.get(partner_id)
        if not partner:
            return

        if not vals.get('segment'):
            vals['segment'] = partner.segment
        if not vals.get('channel'):
            vals['channel'] = partner.channel

    def _sync_segment_channel_to_partner(self):
        for lead in self.filtered('partner_id'):
            partner_updates = {}
            if lead.segment and lead.partner_id.segment != lead.segment:
                partner_updates['segment'] = lead.segment
            if lead.channel and lead.partner_id.channel != lead.channel:
                partner_updates['channel'] = lead.channel
            if partner_updates:
                lead.partner_id.write(partner_updates)
