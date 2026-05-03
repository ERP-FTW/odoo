# -*- coding: utf-8 -*-
{
    'name': 'POS Crypto Payments - NowPayments',
    'author': "MLR - MI Lightning Rod",
    'version': '18.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a large number of on-chain cryptocurrencies through NowPayments',
    'description': '',
    'data': [
        'views/pos_payment_method.xml',
    ],
    'images': ['static/description/icon.png'],
    'depends': ['point_of_sale', 'mlr_pos_cryptopayments'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'mlr_pos_nowpayments/static/src/js/payment_nowpayments.js',
            'mlr_pos_nowpayments/static/src/js/validate_payment_screen.js',
            'mlr_pos_nowpayments/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
    'price': '50.00',
    'currency': 'USD',
}
