{
    'name': 'Smart Import Manufacturing',
    'version': '18.0.1.0.0',
    'summary': 'Fulcrum inventory import pack for Smart Import',
    'license': 'LGPL-3',
    'depends': ['smart_import_base', 'smart_import_product', 'smart_import_stock', 'smart_import_mrp'],
    'data': [
        'security/ir.model.access.csv',
        'data/mapping_profile_data.xml',
        'data/import_rule_data.xml',
        'views/import_session_views.xml',
    ],
    'installable': True,
    'application': False,
}
