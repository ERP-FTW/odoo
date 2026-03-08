from odoo import models, fields, api
import os
import paramiko
from lxml import etree
import base64

class SFTPImport(models.Model):
    _name = 'sftp.import'
    _description = 'FTP Sale Order Import'

    name = fields.Char(string='Task Name', default="SFTP Import Task")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('error', 'Error')
    ], default='draft', string="Status")

    ftp_backend_id = fields.Many2one('ftp.sale.order.backend', string="FTP Backend Configuration", required=True)

    @api.model
    def set_ftp_backend(self):
        """Fetch the first 'connected' FTP backend and set it to the current SFTP import."""
        connected_backend = self.env['ftp.sale.order.backend'].search([('state', '=', 'connected')], limit=1)
        if not connected_backend:
            raise ValueError("No connected FTP backend configuration found.")
        self.ftp_backend_id = connected_backend.id

    @api.model
    def set_ftp_backend(self):
        """Fetch the first 'connected' FTP backend and set it to the current SFTP import."""
        connected_backend = self.env['ftp.sale.order.backend'].search([('state', '=', 'connected')], limit=1)
        if not connected_backend:
            raise ValueError("No connected FTP backend configuration found.")
        self.ftp_backend_id = connected_backend.id

    @api.model
    def download_file_from_sftp(self):
        """
        Download multiple files from the SFTP server and process them to create sale orders.
        Uses configuration data from the FtpSaleOrderBackend model.
        """
        connected_backend = self.env['ftp.sale.order.backend'].search([('state', '=', 'connected')], limit=1)
        try:
            self.set_ftp_backend()
            host = connected_backend.host
            port = connected_backend.port
            username = connected_backend.username
            password = connected_backend.password
            remote_directory = connected_backend.directory

            file_names = self.get_sftp_files_list(host, port, username, password, remote_directory)
            for file_name in file_names:
                remote_path = os.path.join(remote_directory, file_name)
                self.download_file_from_sftp_logic(host, port, username, password, remote_path)
                self.create_sale_order_from_xml(file_name)
            self.state = 'done'
        except Exception as e:
            self.state = 'error'
            raise Exception(f"SFTP download or Sale Order creation failed: {str(e)}")

    def get_sftp_files_list(self, host, port, username, password, remote_directory):
        """
        Get the list of files in the specified directory on the SFTP server.
        """
        try:
            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)

            sftp = paramiko.SFTPClient.from_transport(transport)
            file_names = sftp.listdir(remote_directory)  # List all files in the remote directory
            sftp.close()
            transport.close()
            return file_names

        except Exception as e:
            print(f"SFTP file listing failed: {str(e)}")
            raise

    def download_file_from_sftp_logic(self, host, port, username, password, remote_path):
        """
        Handle SFTP file download logic and store file data in the model.
        Also, link the downloaded XML file to the Sale Order's sftp_attachment_id.
        """
        try:

            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            file_data = sftp.open(remote_path, 'rb').read()
            sftp.close()
            transport.close()

            if not file_data:
                raise ValueError(f"Downloaded file {remote_path} is empty.")

            attachment = self.env['ir.attachment'].create({
                'name': os.path.basename(remote_path),
                'type': 'binary',
                'datas': base64.b64encode(file_data),
                'mimetype': 'application/xml',
                'res_model': 'sftp.import',
                'res_id': self.id
            })
            sale_order = self.env['sale.order'].search([('state', '=', 'draft')],
                                                       limit=1)
            if sale_order:
                sale_order.sftp_attachment_id = attachment.id
            return attachment

        except Exception as e:
            raise Exception(f"SFTP download failed: {str(e)}")

    def create_sale_order_from_xml(self, file_name):
        """
        Parse the downloaded XML file (from the attachment) and create a sale order in Odoo.
        """
        try:

            attachment = self.env['ir.attachment'].search([('name', '=', file_name)], limit=1)
            if not attachment:
                raise Exception(f"No attachment found for file {file_name}.")

            file_data = base64.b64decode(attachment.datas)
            tree = etree.fromstring(file_data)
            namespaces = {
                'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
                'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
            }

            order_id = tree.xpath('.//cbc:ID', namespaces=namespaces)[0].text
            customer_name = \
                tree.xpath('.//cac:BuyerCustomerParty/cac:Party/cac:PartyName/cbc:Name', namespaces=namespaces)[0].text
            customer_email = None

            existing_order = self.env['sale.order'].search([('name', '=', order_id)], limit=1)
            if existing_order:
                print(f"Sale Order {order_id} already exists. Skipping creation.")
                return

            partner = self.env['res.partner'].search([('name', '=', customer_name)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': customer_name,
                    'email': customer_email,
                })

            order_lines = []
            for line in tree.xpath('.//cac:OrderLine/cac:LineItem', namespaces=namespaces):
                product_name = line.xpath('.//cbc:Name', namespaces=namespaces)[0].text
                quantity = float(line.xpath('.//cbc:Quantity', namespaces=namespaces)[0].text)
                price = float(line.xpath('.//cbc:PriceAmount', namespaces=namespaces)[0].text)

                # Create a product if it doesn't exist
                product = self.env['product.product'].search([('name', '=', product_name)], limit=1)
                if not product:
                    product = self.env['product.product'].create({
                        'name': product_name,
                        'list_price': price,
                        'standard_price': price,
                    })

                order_lines.append({
                    'product_name': product_name,
                    'quantity': quantity,
                    'price': price
                })
            sale_order = self.create_sale_order(partner, order_lines, order_id)
            self.attach_file_to_chatter(sale_order, attachment)
            self.notify_sales_manager(sale_order)
        except Exception as e:
            raise Exception(f"Error parsing XML or creating sale order: {str(e)}")

    def create_sale_order(self, partner, order_lines, order_id):
        """
        Create the Sale Order in Odoo and confirm it.
        """
        sale_order = self.env['sale.order'].create({
            'name': order_id,  # Set the order ID to ensure uniqueness
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': []
        })

        # Add order lines
        for line in order_lines:
            product = self.env['product.product'].search([('name', '=', line['product_name'])], limit=1)
            if product:
                sale_order.write({
                    'order_line': [(0, 0, {
                        'product_id': product.id,
                        'product_uom_qty': line['quantity'],
                        'price_unit': line['price'],
                    })]
                })
        sale_order.action_confirm()
        return sale_order

    def attach_file_to_chatter(self, sale_order, attachment):
        """
        Attach the UBL XML data to the Sale Order's chatter.
        """
        try:
            sale_order.message_post(
                body="UBL XML file attached",
                message_type='notification',
                attachment_ids=[attachment.id]
            )
            sale_order.write({'sftp_attachment_id': attachment.id})
            print(f"UBL XML file attached to Sale Order {sale_order.name}.")

        except Exception as e:
            print(f"Error attaching file to chatter: {str(e)}")
            raise Exception(f"Error attaching file to chatter: {str(e)}")

    def notify_sales_manager(self, sale_order):
        """
        Notify the Sales Manager about the newly created Sale Order.
        """
        sales_manager_group = self.env.ref('sales_team.group_sale_manager')

        if sales_manager_group:
            sales_managers = sales_manager_group.users
            sale_order.message_post(
                body=f"New Sale Order {sale_order.name} has been created and confirmed.",
                message_type='notification',
                partner_ids=[manager.id for manager in sales_managers]
            )


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sftp_attachment_id = fields.Many2one(
        'ir.attachment',
        string="SFTP Downloaded File",
        help="The file that was downloaded from the FTP server."
    )
