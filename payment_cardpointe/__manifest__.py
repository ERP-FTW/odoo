{
    'name': 'CardPointe Payment',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'CardPointe payment integration for e-commerce',
    'description': 'CardPointe payment integration for website checkout.',
    'depends': ['payment', 'payment_cardpointe_base', 'website_sale'],
    'data': [
        'views/payment_templates.xml',
        'views/payment_provider_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_cardpointe/static/src/js/payment_form.js',
        ],
    },
    'license': 'LGPL-3',
}
