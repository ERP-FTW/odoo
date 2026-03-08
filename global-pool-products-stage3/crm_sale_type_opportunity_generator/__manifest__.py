{
    'name': 'CRM Sale Type Opportunity Generator',
    'version': '18.0.1.0.0',
    'summary': 'Generate CRM opportunities from historical sales by sale type',
    'category': 'Sales/CRM',
    'depends': ['crm', 'sale_management', 'sale_order_sale_type'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'wizard/generate_sale_type_opportunities_wizard_views.xml',
        'views/crm_team_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
