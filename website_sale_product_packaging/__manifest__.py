{
    'name': 'Website Sale Product Packaging',
    'version': '18.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Sell products by package on eCommerce while storing native packaging metadata.',
    'depends': ['website_sale', 'sale_management', 'product', 'mail'],
    'data': [
        'views/product_packaging_views.xml',
        'views/product_template_views.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_product_packaging/static/src/js/website_sale_product_packaging.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
}
