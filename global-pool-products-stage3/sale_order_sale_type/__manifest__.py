{
    'name': 'Sale Order Sale Type',
    'version': '18.0.1.0',
    'category': 'Sales',
    'summary': 'Adds Sale Type to Sales Orders and Reporting',
    'depends': ['sale', 'sale_management'],
    'data': [
        'views/sale_order_views.xml',
        'security/ir.model.access.csv',
        'data/sale_type_data.xml',
        'views/sale_report_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
