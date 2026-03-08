/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { rpc, jsonrpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";

// Get the default SignatureForm from the registry
const SignatureForm = registry.category("public_components").get("portal.signature_form");

// Patch the SignatureForm prototype
patch(SignatureForm.prototype, {


    async setup() {
        // Call the parent setup to maintain default behavior
        await super.setup();
        const params = await rpc("/signature/get_config", {});
        this.docCheckbox = params.document_review_checkbox_enabled === 'True'? true: false;
        this.docLabel = params.document_review_checkbox_label;
        this.dialogService = registry.category("services").get("dialog", null);
    },

    async onClickSubmit(...args) {
        const che = $('.document_reviewed')
            if ((!che) || (che[0] && !che[0].checked)) { // Checks if the value is not 'on' (likely a checkbox)
//                this.dialogService.add(ConfirmationDialog, {
//                    body, title: _t("Terms and Condition"),
//                    confirm: () => {},
//                    close: () => reject,
//                });
                    this.env.services.dialog.add(WarningDialog, { // Opens a warning dialog
                        title: _t("Document Review Confirmation Needed"), // Translated title
                        message: _t("Could you confirm that you've reviewed the document?"),
                    });
                    return; // Exits the function if the condition fails
                }

        const job_title = $('.job_title').val();
        const data = await rpc(this.props.callUrl, { job_title });
        await super.onClickSubmit(...args); // Pass args to parent method if needed
    },
});
