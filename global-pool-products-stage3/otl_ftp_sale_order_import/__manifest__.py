{
    'name': 'Sale Order FTP Transfer',
    'version': '1.0',
    'category': 'Sales',
    'author': 'Global Pool Products',
    'depends': ['base','sale','mail','sales_team'],
    'data': [
        'data/scheduled_actions.xml',
        'security/ir.model.access.csv',
        'views/ftp_backend_view.xml',
        'views/sftp_import_view.xml',
        'views/ir_attachment.xml',
    ],

    'installable': True,
    'auto_install': False,
}
