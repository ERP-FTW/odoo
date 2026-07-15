{
    'name': 'POS Tips Cashout Policy',
    'version': '18.0.1.0.0',
    'summary': 'Policy-based POS tip pool and tip-out cashout calculations',
    'category': 'Sales/Point of Sale',
    'depends': ['pos_tip_cashout_direct', 'point_of_sale', 'pos_restaurant', 'pos_hr', 'hr', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_tip_policy_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_tips_cashout_policy/static/src/app/**/*',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
