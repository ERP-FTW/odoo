{
    'name': 'Custom Commissions Plan',
    'version': '1.0',
    'summary': 'Adds customer-specific commission percentages',
    'sequence': 10,
    'description': """Allow setting commission rates per customer.""",
    'category': 'Customization',
    'depends': ['base','sale','sale_commission'],
    'data': [
        'views/commission_plan_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
