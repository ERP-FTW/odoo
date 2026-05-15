# Website Sale Packaging Selector

This module backports practical eCommerce package selector behavior from newer Odoo branches into Odoo 18.0.

## Why this module exists

It intentionally does **not** cherry-pick upstream Odoo commit `6a720dc3983292fe27595fdf712de750049a4d65` (`[FW][IMP] *: remove uom categories and merge packaging into uom`) because that commit is a broad core refactor across many applications.

Instead, this module mimics the eCommerce behavior using Odoo 18.0 native objects:
- `product.packaging`
- `sale.order.line.product_packaging_id`
- `sale.order.line.product_packaging_qty`
- `sale.order.line.product_uom_qty`

## Features

- Configurable package availability for website.
- Product-level mode to sell by packages only or by units and packages.
- Package-aware cart line matching to avoid merging packaged and unit lines.
- Conversion of package quantity to unit quantity before standard cart update.
- Cart display with package quantity and equivalent units.
