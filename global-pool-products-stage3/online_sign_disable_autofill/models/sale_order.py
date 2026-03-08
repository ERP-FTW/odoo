from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    job_title = fields.Char()
    docs_reviewed = fields.Boolean(
        string="Document Reviewed",
        compute="_compute_docs_reviewed",
        store=True,
        help="Reflects the current value of the Document Review Checkbox setting."
    )

    @api.depends()  # No dependency needed since it’s based on a global setting
    def _compute_docs_reviewed(self):
        """Set docs_reviewed based on the current value of document_review_checkbox_enabled."""
        icp = self.env['ir.config_parameter'].sudo()
        setting_value = icp.get_param('ott_online_sign_disable_autofill.document_review_checkbox_enabled',
                                      default=False)
        for record in self:
            record.docs_reviewed = setting_value

    @api.model_create_multi
    def create(self, vals_list):
        icp = self.env['ir.config_parameter'].sudo()
        setting_value = icp.get_param('ott_online_sign_disable_autofill.document_review_checkbox_enabled',
                                      default=False)
        for vals in vals_list:
            vals['docs_reviewed'] = setting_value  # Force the value at creation
            if vals.get('job_title'):
                self.env['res.partner'].browse(vals['partner_id']).write({'function': vals['job_title']})
        return super().create(vals_list)


    def write(self, values):
        if values.get('job_title'):
            self.partner_id.write({'function': values['job_title']})
        if 'document_reviewed' in values:
            self.document_reviewed = values['document_reviewed']
        return super().write(values)
