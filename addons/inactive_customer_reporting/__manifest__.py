# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Inactive Customer Reporting',
    'version': '16.0.1.0.0',
    'summary': 'Expose customer last confirmed order date in Sales Analysis.',
    'category': 'Sales/Reporting',
    'license': 'LGPL-3',
    'depends': ['sale'],
    'data': [
        'views/sale_report_views.xml',
    ],
    'installable': True,
    'application': False,
}
