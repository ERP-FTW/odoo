{
    'name': 'Website Sale Packaging Selector',
    'version': '18.0.1.0.0',
    'category': 'Website/eCommerce',
    'summary': 'Sell product units via package selector on eCommerce',
    'depends': ['website_sale', 'sale_management', 'product'],
    'data': [
        'views/product_packaging_views.xml',
        'views/product_template_views.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_packaging_selector/static/src/js/website_sale_packaging_selector.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
}
