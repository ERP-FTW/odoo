{
    'name': 'Smart Import Base',
    'version': '18.0.1.0.0',
    'summary': 'Generic framework for spreadsheet imports',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/import_session_views.xml',
        'views/mapping_profile_views.xml',
        'views/import_rule_views.xml',
        'views/import_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
}
