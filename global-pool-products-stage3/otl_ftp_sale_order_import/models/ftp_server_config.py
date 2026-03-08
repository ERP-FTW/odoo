from odoo import models, fields, api, _
import paramiko
import base64
import logging

from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class FtpSaleOrderBackend(models.Model):
    _name = 'ftp.sale.order.backend'
    _description = 'FTP Mail Server'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, help='A unique identifier for the FTP backend configuration.')
    host = fields.Char(string='FTP Server', required=True, help='The hostname or IP address of the FTP server.')
    port = fields.Integer(string='Port', default=22, required=True,
                          help='The port number for the SFTP connection (default 22).')
    username = fields.Char(string='Username', required=True, help='The username for SFTP authentication.')
    password = fields.Char(string='Password', required=True, help='The password for SFTP authentication.',
                           password=True)
    directory = fields.Char(string='FTP Directory', required=True,
                            help='The directory path on the SFTP server for file retrieval.')
    state = fields.Selection([
        ('connected', "Connected"),
        ('not_connected', "Not Connected"),
    ], string='Connection Status', default='not_connected')

    active = fields.Boolean('Active', default=True)

    @api.constrains('port')
    def _check_port(self):
        """Validate that the port number is within a valid range."""
        for record in self:
            if not 1 <= record.port <= 65535:
                raise ValidationError(_("The port number must be between 1 and 65535."))

    def action_test_connection(self):
        """Manually test the SFTP connection and display the result."""
        self.ensure_one()
        try:
            transport = paramiko.Transport((self.host, self.port))
            transport.connect(username=self.username, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.listdir()
            sftp.close()
            transport.close()
            self.state = 'connected'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Successfully connected to the SFTP server.'),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client',
                             'tag': 'reload'},
                },
            }
        except Exception as e:
            _logger.error("Manual SFTP connection test failed for %s: %s", self.name, str(e))
            self.state = 'not_connected'
            raise UserError(_("Failed to connect to the SFTP server: %s") % str(e))

    def action_reset_connection(self):
        """Reset the connection status to 'not_connected'."""
        self.ensure_one()
        self.state = 'not_connected'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection Disconnected'),
                'message': _('Connection has been reset to "Not Connected."'),
                'type': 'danger',
                'sticky': False,
                'next': {'type': 'ir.actions.client',
                         'tag': 'reload'},
            },
        }