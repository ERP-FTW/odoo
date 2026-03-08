{
    'name': 'Online Sign Disable Autofill',
    'version': '1.0',
    'description': 'Client Signature Customizations',
    'summary': '''
    - Customization in Costumer Portal signature Popup
    - Customization in Sale Order report
    ''',
    'author': 'Odoo, Inc.',
    'website': 'www.odoo.com',
    'license': 'OPL-1',
    'category': 'Customization',
    'depends': ['sale', 'web', 'portal'],
    'data': [
        'views/sale_portal_templates.xml',
        'views/document_review_sale_order.xml',
        'views/res_config.xml',
        'report/ir_actions_report_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'online_sign_disable_autofill/static/src/js/portal_signature.js',
            'online_sign_disable_autofill/static/src/xml/portal_signature.xml',
        ]
    },
    'auto_install': False,
    'application': False,
    'module_type': 'official',
    'installable': True,
}
