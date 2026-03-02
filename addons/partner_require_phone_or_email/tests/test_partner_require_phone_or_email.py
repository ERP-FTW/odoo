from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPartnerRequirePhoneOrEmail(TransactionCase):

    def test_create_partner_without_contact_method_fails(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'No Contact Method',
                'email': False,
                'phone': False,
                'mobile': False,
            })

    def test_create_partner_with_email_works(self):
        partner = self.env['res.partner'].create({
            'name': 'With Email',
            'email': 'email@example.com',
        })
        self.assertTrue(partner)

    def test_create_partner_with_phone_works(self):
        partner = self.env['res.partner'].create({
            'name': 'With Phone',
            'phone': '+1555000100',
        })
        self.assertTrue(partner)

    def test_remove_last_contact_method_fails_on_write(self):
        partner = self.env['res.partner'].create({
            'name': 'Remove Last Contact Method',
            'email': 'present@example.com',
        })
        with self.assertRaises(ValidationError):
            partner.write({
                'email': '   ',
                'phone': False,
                'mobile': False,
            })

    def test_excluded_partners_are_not_blocked(self):
        company_partner = self.env.company.partner_id
        company_partner.write({
            'email': False,
            'phone': False,
            'mobile': False,
        })

        user = self.env['res.users'].create({
            'name': 'No Contact User',
            'login': 'noconctuser2',
            'email': False,
        })
        user.partner_id.write({
            'email': False,
            'phone': False,
            'mobile': False,
        })
        self.assertTrue(user.partner_id)

    def test_duplicate_email_prevented(self):
        self.env['res.partner'].create({
            'name': 'Email A',
            'email': 'Test@Example.com',
        })
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Email B',
                'email': ' test@example.com ',
            })

    def test_duplicate_phone_prevented(self):
        self.env['res.partner'].create({
            'name': 'Phone A',
            'phone': '(313) 555-0101',
        })
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Phone B',
                'mobile': '3135550101',
            })

    def test_cross_field_collision_prevented(self):
        self.env['res.partner'].create({
            'name': 'Cross A',
            'mobile': '3135550102',
        })
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Cross B',
                'phone': '313-555-0102',
            })

    def test_allow_distinct_contact_methods(self):
        partner_a = self.env['res.partner'].create({
            'name': 'Distinct A',
            'email': 'a@example.com',
            'phone': '3135550199',
        })
        partner_b = self.env['res.partner'].create({
            'name': 'Distinct B',
            'email': 'b@example.com',
            'phone': '3135550200',
        })
        self.assertTrue(partner_a and partner_b)

    def test_archived_partner_does_not_block_active_duplicate(self):
        partner_a = self.env['res.partner'].create({
            'name': 'Archive A',
            'phone': '3135550103',
        })
        partner_a.active = False
        partner_b = self.env['res.partner'].create({
            'name': 'Archive B',
            'phone': '3135550103',
        })
        self.assertTrue(partner_b)
