# Copyright 2024 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Tracking reference on Sales Order propagates to Invoice and Delivery',
    'version': '18.0.3.0.0',
    'description': 'Delivery Tracking Reference on the Sale Order to Delivery and Invoice form and PDF Invoice.',
    'summary': '''
       - Delivery Tracking Reference on the Invoice form and PDF Invoice. 
       ''',
    'author': 'One Team',
    'website': 'www.oneteam.us',
    'license': 'OPL-1',
    'category': 'Customization',
    'sequence': 155,
    "depends": ["account", "sale", "sale_stock", "stock", "delivery" ],
    "data": [
             'views/account_move.xml',
             'views/sale_order.xml',
             'views/choose_delivery_carrier.xml',
             'report/invoice_report.xml'
             ],
    'auto_install': False,
    'application': False,
}
