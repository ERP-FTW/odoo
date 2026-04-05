# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'MLR POS Bitcoin Payments - Breez',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 7,
    'summary': 'Integrate your POS with Bitcoin lightning payments using Breez',
    'description': '',
    'data': [
        'views/pos_payment_method.xml',
    ],
    'module_type': 'official',
    'depends': ['point_of_sale', 'mlr_pos_cryptopayments'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'mlr_pos_breez_greenlight/static/src/js/models.js',
            'mlr_pos_breez_greenlight/static/src/js/payment_cryptopayment.js',
        ],
    },
    'license': 'LGPL-3',
}
