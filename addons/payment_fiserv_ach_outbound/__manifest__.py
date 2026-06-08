{
    'name': 'Payment Fiserv ACH Outbound',
    'version': '16.0.1.0.0',
    'summary': 'Outbound vendor ACH over Fiserv/CardPointe',
    'depends': ['account_payment_outbound_base', 'payment', 'account'],
    'data': [
        'views/payment_provider_views.xml',
        'views/res_partner_bank_views.xml',
    ],
    'license': 'LGPL-3',
}
