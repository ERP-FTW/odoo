from odoo.tests import common


class TestPartnerCrmSegmentChannel(common.TransactionCase):

    def test_partner_prefill_to_lead(self):
        partner = self.env['res.partner'].create({
            'name': 'Acme',
            'segment': 'retail',
            'channel': 'web',
        })

        lead = self.env['crm.lead'].create({
            'name': 'Lead A',
            'partner_id': partner.id,
        })

        self.assertEqual(lead.segment, 'retail')
        self.assertEqual(lead.channel, 'web')

    def test_lead_write_back_to_partner(self):
        partner = self.env['res.partner'].create({
            'name': 'Acme',
            'segment': 'retail',
            'channel': 'web',
        })
        lead = self.env['crm.lead'].create({
            'name': 'Lead B',
            'partner_id': partner.id,
        })

        lead.write({'segment': 'vip', 'channel': 'event'})

        self.assertEqual(partner.segment, 'vip')
        self.assertEqual(partner.channel, 'event')

    def test_lead_conversion_preserves_values(self):
        lead = self.env['crm.lead'].create({
            'name': 'Lead C',
            'segment': 'wholesale',
            'channel': 'referral',
        })

        lead._handle_partner_assignment(create_missing=True)

        self.assertTrue(lead.partner_id)
        self.assertEqual(lead.partner_id.segment, 'wholesale')
        self.assertEqual(lead.partner_id.channel, 'referral')

    def test_views_load(self):
        self.env['res.partner'].get_view(
            view_id=self.env.ref('partner_crm_segment_channel.view_res_partner_filter_segment_channel').id,
            view_type='search',
        )
        self.env['res.partner'].get_view(
            view_id=self.env.ref('partner_crm_segment_channel.view_res_partner_pivot_segment_channel').id,
            view_type='pivot',
        )
        self.env['crm.lead'].get_view(
            view_id=self.env.ref('partner_crm_segment_channel.crm_lead_view_form_segment_channel').id,
            view_type='form',
        )
