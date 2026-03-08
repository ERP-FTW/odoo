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
            'login': 'noconctuser',
            'email': False,
        })
        user.partner_id.write({
            'email': False,
            'phone': False,
            'mobile': False,
        })
        self.assertTrue(user.partner_id)

    def test_duplicate_email_is_warning_only(self):
        self.env['res.partner'].create({
            'name': 'Original Email',
            'email': 'duplicate@example.com',
        })
        duplicate = self.env['res.partner'].create({
            'name': 'Duplicate Email',
            'email': 'DUPLICATE@example.com',
        })
        self.assertTrue(duplicate)
        self.assertTrue(duplicate.has_duplicate_email_warning)
        self.assertTrue(duplicate.has_contact_duplicate_warning)

    def test_duplicate_phone_mobile_cross_field_is_warning_only(self):
        self.env['res.partner'].create({
            'name': 'Original Phone',
            'phone': '+1 (555) 000 1111',
        })
        duplicate = self.env['res.partner'].create({
            'name': 'Duplicate Mobile',
            'mobile': '1-555-000-1111',
        })
        self.assertTrue(duplicate)
        self.assertTrue(duplicate.has_duplicate_mobile_warning)
        self.assertTrue(duplicate.has_contact_duplicate_warning)

    def test_duplicate_flags_not_set_when_not_required(self):
        company_partner = self.env.company.partner_id
        company_partner.write({'email': 'company@example.com'})

        other = self.env['res.partner'].create({
            'name': 'Other Company Email',
            'email': 'company@example.com',
        })
        self.assertFalse(company_partner.has_contact_duplicate_warning)
        self.assertTrue(other.has_contact_duplicate_warning)
