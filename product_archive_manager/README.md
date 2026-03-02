# Product Archive Manager

## What this module does

This module controls who can archive/unarchive products and adds traceability when product archival state changes.

- Adds security group **Can archive/unarchive products** (`product_archive_manager.group_product_archive_toggle`).
- Prevents users outside this group from toggling `active` on product templates and product variants.
- Logs successful archive/unarchive actions:
  - In the product chatter (`mail.mt_note`)
  - In the server log (`_logger.warning`) with selected context keys and stack trace
- Supports an optional bypass via context key: `allow_product_archive=True`.

## Permission setup

1. Go to **Settings > Users & Companies > Users**.
2. Open a user.
3. In access rights/groups, grant **Can archive/unarchive products**.

Users without this group can still edit product fields, but cannot archive/unarchive.

## Where to find traces

- **Chatter:** Open product template or variant form, see note entries for archive/unarchive actions.
- **Server logs:** Look for warning logs from this module including model, ids, uid, context breadcrumb, and stack trace.

## Bypass option (for technical scripts)

Use:

```python
products.with_context(allow_product_archive=True).write({"active": False})
```

Bypass usage is also logged with uid/model/ids.

## Duplicate logging strategy

Both `product.template` and `product.product` enforce permission. To avoid duplicate trace entries from template/variant cascades, writes are executed with `product_archive_trace_logged=True` in context before `super().write(vals)`. The logging helper checks this context flag and only logs when not already flagged.

## Test plan

1. **Normal user (without group)**
   - Edit product name: should work.
   - Archive/unarchive product: should raise `AccessError`.

2. **User with archive group**
   - Archive product (single): should succeed.
   - Unarchive product (single): should succeed.
   - Verify one chatter note per action.
   - Verify server log contains warning with stack trace.

3. **Multi-record archive from list view**
   - Archive multiple products in one action: should succeed for authorized user.
   - Verify notes are created on affected records.
   - Verify no duplicate notes from template/variant cascade.

4. **Bypass context**
   - Use `with_context(allow_product_archive=True)` in script for non-group user.
   - Operation should succeed and bypass warning should be present in logs.
