{
    'name': 'Custom Commissions',
    'version': '1.0',
    'summary': 'Adds customer-specific commission percentages',
    'sequence': 10,
    'description': """Allow setting commission rates per customer.""",
    'category': 'Customization',
    'depends': ['base','sale','sale_commission'],  # Ensure this includes all necessary dependencies.
    'data': [
        'views/commission_plan_view.xml',  # Add your view modifications here
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
