{
    'name': 'Account Payment Outbound Base',
    'version': '16.0.1.0.0',
    'summary': 'Generic outbound provider framework for vendor payments',
    'depends': ['account', 'payment'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
    ],
    'license': 'LGPL-3',
}
