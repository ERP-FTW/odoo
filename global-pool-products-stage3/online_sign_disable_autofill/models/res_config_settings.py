from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _name = 'res.config.settings'
    _inherit = 'res.config.settings'

    document_review_checkbox_enabled = fields.Boolean(
        string="Document Review Checkbox",
        config_parameter='ott_online_sign_disable_autofill.document_review_checkbox_enabled',
    )
    document_review_checkbox_label = fields.Char(
        string="Checkbox Label",
        config_parameter='ott_online_sign_disable_autofill.document_review_checkbox_label',
        translate=True,
        default="I acknowledge that I have reviewed the documents.",
    )
    document_review_url = fields.Char(string='Document Review URL', help="URL to the document review page or details")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        icp = self.env['ir.config_parameter'].sudo()

        # Get the values for the new fields
        document_review_checkbox_enabled = icp.get_param(
            'ott_online_sign_disable_autofill.document_review_checkbox_enabled', False)
        document_review_checkbox_label = icp.get_param(
            'ott_online_sign_disable_autofill.document_review_checkbox_label',
            'I acknowledge that I have reviewed the documents.')

        # Update the values with the new fields
        res.update({
            'document_review_checkbox_enabled': document_review_checkbox_enabled,
            'document_review_checkbox_label': document_review_checkbox_label,
        })
        return res

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        icp = self.env['ir.config_parameter'].sudo()

        # Set the values for the new fields
        icp.set_param('ott_online_sign_disable_autofill.document_review_checkbox_enabled',
                      self.document_review_checkbox_enabled)
        icp.set_param('ott_online_sign_disable_autofill.document_review_checkbox_label',
                      self.document_review_checkbox_label)
