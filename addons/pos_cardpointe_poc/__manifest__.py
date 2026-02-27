{
    'name': 'POS CardPointe POC',
    'version': '16.0.1.0.0',
    'summary': 'POC CardPointe terminal integration for POS',
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/cardpointe_terminal_config_views.xml',
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_cardpointe_poc/static/src/js/pos_cardpointe_poc.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
