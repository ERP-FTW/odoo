import binascii
import logging
from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):

    def portal_quote_accept(self, order_id, access_token=None, name=None, signature=None, job_title=None):
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            # Access check
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError) as e:
            _logger.error(f"Access denied for order {order_id} with token {access_token}: {e}")
            return {'error': _('Invalid order.')}

        try:
            # Write operation
            if job_title:
                order_sudo.write({'job_title': job_title})
        except (TypeError, binascii.Error) as e:
            _logger.error(f"Invalid signature or job title data for order {order_id}: {e}")
            return {'error': _('Invalid signature data.')}

        _logger.info(f"Successfully processed order {order_id}")
        return super().portal_quote_accept(order_id, access_token, name, signature)

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        # Add configuration settings to the template values
        config = request.env['ir.config_parameter'].sudo()
        values['config'] = {
            'document_review_checkbox_enabled': config.get_param(
                'ott_online_sign_disable_autofill.document_review_checkbox_enabled', False),
            'document_review_checkbox_label': config.get_param(
                'ott_online_sign_disable_autofill.document_review_checkbox_label',
                'I acknowledge that I have reviewed the documents.'),
        }
        return values

    @http.route('/signature/get_config', type='json', auth='public')
    def get_signature_config(self):
        # Fetch system parameters
        document_review_checkbox_enabled = request.env['ir.config_parameter'].sudo().get_param(
            'ott_online_sign_disable_autofill.document_review_checkbox_enabled', default=False)
        document_review_checkbox_label = request.env['ir.config_parameter'].sudo().get_param(
            'ott_online_sign_disable_autofill.document_review_checkbox_label', default=False)

        return {
            'document_review_checkbox_label': document_review_checkbox_label,
            'document_review_checkbox_enabled': document_review_checkbox_enabled,
        }
