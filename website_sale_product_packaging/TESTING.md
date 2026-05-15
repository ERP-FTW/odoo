# Website Sale Product Packaging - Testing

## Behavior choice for packaging-only products
If a packaging-only product is submitted without `website_packaging_id`, the module auto-selects the product's default website packaging. If no default/published packaging exists, a `UserError` is raised.

## Manual test steps
1. Create Product A with UoM Units.
2. Add Packaging "Box of 25" with qty `25`, check `Available on eCommerce`, check `Default eCommerce Package`.
3. Set Product A `eCommerce Package Sale Mode` to `Packages only`.
4. Open product page: package selector should not allow Units.
5. Add quantity `1`: sale order line should have packaging qty `1` and unit qty `25`.
6. Add quantity `2`: sale order line should have packaging qty `2` and unit qty `50`.
7. From cart, change packaged quantity `2 -> 3`: line should move to unit qty `75`.
8. Set mode to `Allow units and packages`: verify Units and packaging can be selected.
9. Add units qty `5` and one box qty `1`: verify two separate lines.
10. Tamper `website_packaging_id` with package of another product: verify `UserError`.
11. Confirm order and verify downstream flows still work with unit quantities.
