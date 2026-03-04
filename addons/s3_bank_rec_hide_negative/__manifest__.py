{
    'name': 'S3 Bank Reconciliation Hide Negative Lines',
    'version': '18.0.1.0.0',
    'summary': 'Hide negative statement lines in bank reconciliation for selected users',
    'category': 'Accounting/Accounting',
    'author': 'S3',
    'license': 'LGPL-3',
    'depends': ['account_accountant'],
    'data': [
        'security/security.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
}
