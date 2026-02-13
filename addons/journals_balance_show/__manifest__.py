{
    'name': 'Show journal balance',
    'summary': """Show journal balance on account dashboard for selecetd users""",
    'version': '16.0.1.0.1',
    'description': """Show journal balance on account dashboard for selecetd users""",
    'author': 'POD IT Services',
    'company': 'POD IT Services',
    'website': 'https://poditservices.com/',
    'category': 'Tools',
    'depends': ['base', 'account'],
    'license': 'AGPL-3',
    'data': [
        'security/security.xml',
        'views/account_journal_balance_show.xml',
    ],
    'images': ["static/description/assets/screenshots/1.png", "static/description/2.png"],
    'installable': True,
    'auto_install': False,
}
