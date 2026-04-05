from odoo import api, fields, models, _
from odoo.tools import formatLang, float_is_zero
from odoo.exceptions import ValidationError, UserError
try:
   import qrcode
except ImportError:
   qrcode = None
try:
   import base64
except ImportError:
   base64 = None
from io import BytesIO

class PosPayment(models.Model):
   _inherit = "pos.payment"
    
   is_crypto_payment = fields.Boolean('Paid with Crypto')
   cryptopay_payment_type = fields.Char('Crypto payment Type')
   cryptopay_invoice_id = fields.Char('CryptoPay Invoice ID')
   conversion_rate = fields.Float('Conversion rate')
   invoiced_crypto_amount = fields.Float('Invoiced Crypto Amount', digits=(12,8))
   cryptopay_payment_link = fields.Char('CryptoPay Payment Link')
   cryptopay_payment_link_qr_code = fields.Binary('QR Code', compute="_generate_qr") #binary field that is computed into a QR

   def _export_for_ui(self,payment):
      payment_fields = super(PosPayment, self)._export_for_ui(payment)
      payment_fields.update({
         'is_crypto_payment': payment.cryptopay_payment_type,
         'cryptopay_invoice_id': payment.cryptopay_invoice_id,
         'cryptopay_payment_type': payment.cryptopay_payment_type,
         'cryptopay_payment_link': payment.cryptopay_payment_link,
         'invoiced_crypto_amount': payment.invoiced_crypto_amount,
         'conversion_rate': payment.conversion_rate,
         })
      return payment_fields

   def _generate_qr(self): #called by compute field to change binary into QR
       for rec in self:
           if qrcode and base64:
               qr = qrcode.QRCode(
                   version=1,
                   error_correction=qrcode.constants.ERROR_CORRECT_L, #use low error correction to keep QR less complex and small
                   box_size=8,
                   border=4,
               )
               qr.add_data(rec.cryptopay_payment_link)
               qr.make(fit=True)
               img = qr.make_image()
               temp = BytesIO()
               img.save(temp, format="PNG")
               qr_image = base64.b64encode(temp.getvalue())
               rec.update({'cryptopay_payment_link_qr_code': qr_image}) #update the field with QR
           else:
               raise UserError(_('Necessary Requirements To Run This Operation Is Not Satisfied'))
   


