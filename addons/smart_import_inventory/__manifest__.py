{
    'name': 'Smart Import Inventory',
    'version': '16.0.1.0.0',
    'summary': 'Fulcrum inventory import pack for Smart Import',
    'license': 'LGPL-3',
    'depends': ['smart_import_base', 'product', 'stock', 'purchase_stock', 'mrp', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/mapping_profile_data.xml',
        'data/import_rule_data.xml',
        'views/import_session_views.xml',
    ],
    'installable': True,
    'application': False,
}
