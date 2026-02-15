{
    'name': 'CardPointe Base',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Base utilities for CardPointe payments',
    'description': 'Shared CardPointe configuration and API helpers.',
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
