{
    'name': 'POS Tip Cashout Direct',
    'version': '18.0.1.0.0',
    'summary': 'Minimal POS restaurant tip cashout by employee',
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale', 'pos_restaurant', 'pos_hr', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_tip_cashout_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_tip_cashout_direct/static/src/app/**/*',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
