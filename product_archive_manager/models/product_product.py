import logging
import traceback

from odoo import _, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_archive_target_records(self, active_value):
        target_active = bool(active_value)
        return self.filtered(lambda record: bool(record.active) != target_active)

    def _get_archive_context_breadcrumb(self):
        context = self.env.context
        selected_keys = ["active_model", "active_id", "active_ids", "allowed_company_ids", "uid"]
        breadcrumb = {key: context.get(key) for key in selected_keys if key in context}
        if "from_import" in context:
            breadcrumb["from_import"] = context.get("from_import")
        return breadcrumb

    def _check_archive_permission(self):
        if self.env.context.get("allow_product_archive"):
            _logger.warning(
                "Bypassing archive restriction for model=%s ids=%s uid=%s",
                self._name,
                self.ids,
                self.env.uid,
            )
            return
        if not self.env.user.has_group("product_archive_manager.group_product_archive_toggle"):
            raise AccessError(_("You are not allowed to archive/unarchive products."))

    def _log_archive_changes(self, changed_records, target_active):
        if self.env.context.get("product_archive_trace_logged"):
            return

        breadcrumb = self._get_archive_context_breadcrumb()
        action = "UNARCHIVED" if target_active else "ARCHIVED"
        stack = "".join(traceback.format_stack(limit=30))
        _logger.warning(
            "Product archive toggle model=%s ids=%s active=%s uid=%s context=%s\nStack trace:\n%s",
            self._name,
            changed_records.ids,
            target_active,
            self.env.uid,
            breadcrumb,
            stack,
        )

        user = self.env.user
        for record in changed_records:
            default_code = record.default_code and f" / default_code: {record.default_code}" or ""
            body = (
                f"Action: <b>{action}</b><br/>"
                f"User: {user.display_name} (uid={self.env.uid})<br/>"
                f"Record: {record.display_name} (id={record.id}){default_code}<br/>"
                f"Context: {breadcrumb}"
            )
            record.message_post(body=body, subtype_xmlid="mail.mt_note")

    def write(self, vals):
        if "active" not in vals:
            return super().write(vals)

        changed_records = self._get_archive_target_records(vals["active"])
        if not changed_records:
            return super().write(vals)

        self._check_archive_permission()
        target_active = bool(vals["active"])
        updated_self = self.with_context(product_archive_trace_logged=True)
        result = super(ProductProduct, updated_self).write(vals)
        self._log_archive_changes(changed_records, target_active)
        return result
