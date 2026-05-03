# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import werkzeug
import time
import hashlib
import hmac
import base64
from datetime import datetime, timezone

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, AccessError



_logger = logging.getLogger(__name__)
TIMEOUT = 10

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('now', 'Now')]

    # cryptopay server fields
    now_payment_flow = fields.Selection([('payment link','Payment Link'),('direct invoice','Direct Invoice')], string='Payment Flow')
    nowpayments_username = fields.Char(string='NowPayments Email')
    nowpayments_password = fields.Char(string='NowPayments Password')
    now_selected_crypto = fields.Selection([('eth','ETH'),('jasmy','jasmy'),('usdtkava','usdtkava'),('ada','ada'),('mx','mx'),('aave','aave'),('dgmoon','dgmoon'),('ark','ark'),('sun','sun'),('usdtarb','usdtarb'),('dash','dash'),('fdusderc20','fdusderc20'),('srk','srk'),('stpt','stpt'),('maticmainnet','maticmainnet'),('ggtkn','ggtkn'),('tlos','tlos'),('zen','zen'),('vib','vib'),('atom','atom'),('ape','ape'),('gusd','gusd'),('ctsi','ctsi'),('ilv','ilv'),('usdcop','usdcop'),('klv','klv'),('dai','dai'),('front','front'),('usddbsc','usddbsc'),('cspr','cspr'),('chz','chz'),('ttc','ttc'),('flokibsc','flokibsc'),('epic','epic'),('atlas','atlas'),('busdbsc','busdbsc'),('trvl','trvl'),('bat','bat'),('firo','firo'),('rune','rune'),('cult','cult'),('xtz','xtz'),('wbtcmatic','wbtcmatic'),('one','one'),('enj','enj'),('stkk','stkk'),('tenshi','tenshi'),('xlm','xlm'),('jst','jst'),('cusd','cusd'),('quack','quack'),('link','link'),('rep','rep'),('trx','trx'),('dao','dao'),('btc','btc'),('xcur','xcur'),('usdtbsc','usdtbsc'),('shib','shib'),('uni','uni'),('cromainnet','cromainnet'),('ont','ont'),('vet','vet'),('eos','eos'),('kas','kas'),('busdmatic','busdmatic'),('hbar','hbar'),('usdtdot','usdtdot'),('brise','brise'),('dino','dino'),('ntvrk','ntvrk'),('usdp','usdp'),('strax','strax'),('shibbsc','shibbsc'),('algo','algo'),('qtum','qtum'),('tusd','tusd'),('btg','btg'),('fitfi','fitfi'),('bifi','bifi'),('klvmainnet','klvmainnet'),('xyo','xyo'),('near','near'),('om','om'),('zbc','zbc'),('fun','fun'),('usdterc20','usdterc20'),('cudos','cudos'),('gari','gari'),('busd','busd'),('iotx','iotx'),('ethw','ethw'),('sol','sol'),('usdcmatic','usdcmatic'),('coti','coti'),('sxpmainnet','sxpmainnet'),('mana','mana'),('neo','neo'),('brgbsc','brgbsc'),('icx','icx'),('hotcross','hotcross'),('usdcarb','usdcarb'),('zil','zil'),('usdcsol','usdcsol'),('tfuel','tfuel'),('luna','luna'),('ocean','ocean'),('wintrc20','wintrc20'),('pit','pit'),('cake','cake'),('etc','etc'),('bel','bel'),('onigi','onigi'),('idbsc','idbsc'),('eurt','eurt'),('ftt','ftt'),('kiba','kiba'),('tko','tko'),('poolx','poolx'),('bttc','bttc'),('now','now'),('tomo','tomo'),('usdcarc20','usdcarc20'),('usdtmatic','usdtmatic'),('cfx','cfx'),('cvc','cvc'),('dcr','dcr'),('usddtrc20','usddtrc20'),('doge','doge'),('usdtop','usdtop'),('usdtarc20','usdtarc20'),('1inchbsc','1inchbsc'),('ton','ton'),('avn','avn'),('ht','ht'),('id','id'),('rvn','rvn'),('xvg','xvg'),('fil','fil'),('yfi','yfi'),('tup','tup'),('sand','sand'),('etharb','etharb'),('apt','apt'),('fluf','fluf'),('klay','klay'),('zksync','zksync'),('ltc','ltc'),('galaerc20','galaerc20'),('arb','arb'),('nwc','nwc'),('usdj','usdj'),('usdttrc20','usdttrc20'),('marsh','marsh'),('zec','zec'),('dogecoin','dogecoin'),('bttcbsc','bttcbsc'),('pivx','pivx'),('gas','gas'),('cro','cro'),('1inch','1inch'),('babydoge','babydoge'),('hot','hot'),('usdcbsc','usdcbsc'),('grt','grt'),('gal','gal'),('brisemainnet','brisemainnet'),('okb','okb'),('gafa','gafa'),('knc','knc'),('xcad','xcad'),('kibabsc','kibabsc'),('usdtsol','usdtsol'),('matic','matic'),('axs','axs'),('waves','waves'),('xem','xem'),('hex','hex'),('raca','raca'),('bch','bch'),('usdtalgo','usdtalgo'),('dot','dot'),('ftm','ftm'),('pyusd','pyusd'),('egld','egld'),('daiarb','daiarb'),('fdusdbsc','fdusdbsc'),('tloserc20','tloserc20'),('avaxc','avaxc'),('boba','boba'),('sfund','sfund'),('theta','theta'),('rjv','rjv'),('c98','c98'),('pika','pika'),('cns','cns'),('bnbbsc','bnbbsc'),('avax','avax'),('xaut','xaut'),('arpa','arpa'),('arv','arv'),('super','super'),('verse','verse'),('ethbsc','ethbsc'),('divi','divi'),('blocks','blocks'),('dgb','dgb'),('ftmmainnet','ftmmainnet'),('bnbmainnet','bnbmainnet'),('bsv','bsv'),('chr','chr'),('xdc','xdc'),('poodl','poodl'),('bone','bone'),('floki','floki'),('gt','gt'),('kishu','kishu'),('nano','nano'),('nftb','nftb'),('sysevm','sysevm'),('xrp','xrp'),('guard','guard'),('lunc','lunc'),('geth','geth'),('omg','omg'),('leash','leash'),('xmr','xmr'),('tusdtrc20','tusdtrc20'),('kmd','kmd'),('usdc','usdc'),('hoge','hoge'),('keanu','keanu'),('lgcy','lgcy'),('usdcalgo','usdcalgo'),('bad','bad'),], string='Selected Cryptocurrency')
    now_sandbox = fields.Boolean(string='Conducting sandbox testing')
    now_sandbox_case = fields.Selection([('success','success'),('common','common'),('failed','failed'),('partially_paid','partially_paid')], string='Sandbox case to test')


    def call_cryptopay_api(self,payload,api,method,jwt=0):
        try:
            _logger.info("NowPayments API request started: endpoint=%s method=%s", api, method)
            request_url = f"{self.server_url}{api}"
            if jwt == 0:
                headers = {"x-api-key": (self.api_key), "Content-Type": "application/json"}
            if jwt == 1:
                jwt_payload = {"email": self.nowpayments_username,
                               "password": self.nowpayments_password}
                jwt_response = self.call_cryptopay_api(jwt_payload, '/v1/auth', 'POST', 0)
                jwtoken = jwt_response.json()['token']
                headers = {"x-api-key": (self.api_key), "Content-Type": "application/json", "Authorization": "Bearer " + jwtoken}
            _logger.info("NowPayments API call prepared: endpoint=%s method=%s", api, method)
            if method == "GET":
                apiRes=requests.get(request_url, headers=headers, timeout=TIMEOUT)
            elif method == "POST":
                apiRes = requests.post(request_url, json=payload, headers=headers, timeout=TIMEOUT)
            _logger.info("NowPayments API request completed: endpoint=%s status=%s", api, apiRes.status_code)
            return apiRes
        except Exception as e:
            _logger.exception("NowPayments API call failure: endpoint=%s method=%s", api, method)
            raise UserError(_("API call failure: %s", e.args))

    def _test_connection(self):
        if self.use_payment_terminal == 'now':
            return self.call_cryptopay_api({},"/v1/sub-partner","GET", 1)
        else:
            return super()._test_connection()



    def minimum_invoice_amount(self,now_selected_crypto):
        try:
            payload = {
                "pay_currency": now_selected_crypto,}
            minimum_invoice_amount = self.call_cryptopay_api(payload, '/v1/min-amount?currency_from=' + now_selected_crypto + '&fiat_equivalent=usd', 'GET')
            return minimum_invoice_amount
        except Exception as e:
            message = "An exception occurred with Now minimum_invoice_amount: " + str(e)
            _logger.exception(message)
            return {"code": message}

    def create_crypto_invoice_payment_link(self, args, now_sandbox, now_sandbox_case):
        try:
            _logger.info(f"Called Now create_crypto_invoice_payment_link. Passed args are {args}")
            payload = {
                "price_amount": args['amount'],
                "price_currency": self.env.ref('base.main_company').currency_id.name,
                "order_id": args['order_id'],}
            #if now_sandbox == True:
            #    payload["case"] = now_sandbox_case
            create_invoice_api = self.call_cryptopay_api(payload, '/v1/invoice', 'POST')
            if create_invoice_api.status_code != 200:
                return {"code": create_invoice_api.status_code}
            create_invoice_json = create_invoice_api.json()
            inv_json = {
                "code": 0,
                "invoice_id": create_invoice_json['id'],
                "invoice": create_invoice_json['invoice_url'],
                "cryptopay_payment_link": create_invoice_json['invoice_url'],
                "crypto_amt": 'TBD',
                "conversion_rate": 'TBD'}
            _logger.info(f"Completed Now create_crypto_invoice_payment_link. Passing back {inv_json}")
            return inv_json
        except Exception as e:
            message = "An exception occurred with Now create_crypto_invoice_payment_link: " + str(e)
            _logger.exception(message)
            return {"code": message}

    def create_crypto_invoice_direct_invoice(self, args, now_sandbox, now_sandbox_case, now_selected_crypto):
        try:
            _logger.info(f"Called Now create_crypto_invoice_direct_invoice. Passed args are {args}")
            minimum_amount = self.minimum_invoice_amount(now_selected_crypto)
            if minimum_amount.status_code != 200:
                return {"code": minimum_amount.status_code}
            minimum_amount_json = minimum_amount.json()
            minimum_fiat_amount = minimum_amount_json['fiat_equivalent']
            if minimum_fiat_amount > args['amount']:
                return {"code": "Below minimum amount of " + str(self.env.ref('base.main_company').currency_id.symbol) + str(round(minimum_fiat_amount,2)) + " required for " + now_selected_crypto + " payments."}
            payload = {
                "price_amount": args['amount'],
                "price_currency": self.env.ref('base.main_company').currency_id.name,
                "pay_currency": now_selected_crypto,
                "order_id": args['order_id'], }
            if now_sandbox == True:
                payload["case"] = now_sandbox_case
            create_invoice_api = self.call_cryptopay_api(payload, '/v1/payment', 'POST')
            if create_invoice_api.status_code != 201:
                return {"code": create_invoice_api.status_code}
            create_invoice_json = create_invoice_api.json()
            conversion_rate = round(args['amount']/create_invoice_json['pay_amount'],2)
            inv_json = {
                "code": 0,
                "invoice_id": create_invoice_json['payment_id'],
                "invoice": create_invoice_json['pay_address'],
                "cryptopay_payment_link": now_selected_crypto + ":" + create_invoice_json['pay_address'],
                "crypto_amt": round(create_invoice_json['pay_amount'],6),
                "conversion_rate": conversion_rate}
            _logger.info(f"Completed Now create_crypto_invoice_direct_invoice. Passing back {inv_json}")
            return inv_json
        except Exception as e:
            message = "An exception occurred with Now create_crypto_invoice_direct_invoice: " + str(e)
            _logger.exception(message)
            return {"code": message}


    @api.model
    def create_crypto_invoice(self, args):
        try:
            _logger.info("NowPayments invoice creation requested for order_id=%s pm_id=%s", args.get('order_id'), args.get('pm_id'))
            cryptopay_pm = self.env['pos.payment.method'].search([('id', '=', args['pm_id'])], limit=1)
            if cryptopay_pm.use_payment_terminal != 'now':
                return super().create_crypto_invoice(args)
            now_sandbox = cryptopay_pm['now_sandbox']
            now_sandbox_case = ""
            if now_sandbox == True:
                now_sandbox_case = cryptopay_pm['now_sandbox_case']
            now_payment_flow = cryptopay_pm['now_payment_flow']
            if cryptopay_pm.crypto_minimum_amount > args['amount']:
                return {"code": "Below minimum amount of method: "+str(self.env.ref('base.main_company').currency_id.symbol)+str(cryptopay_pm.crypto_minimum_amount)}
            if cryptopay_pm.crypto_maximum_amount < args['amount']:
                return {"code": "Above maximum amount of method: "+str(self.env.ref('base.main_company').currency_id.symbol)+str(cryptopay_pm.crypto_maximum_amount)}
            if now_payment_flow == 'direct invoice':
                now_selected_crypto = cryptopay_pm['now_selected_crypto']
                create_invoice_api = cryptopay_pm.create_crypto_invoice_direct_invoice(args, now_sandbox, now_sandbox_case, now_selected_crypto)
            else:
                create_invoice_api = cryptopay_pm.create_crypto_invoice_payment_link(args, now_sandbox, now_sandbox_case)
            _logger.info("NowPayments invoice creation result for order_id=%s code=%s", args.get('order_id'), create_invoice_api.get('code') if isinstance(create_invoice_api, dict) else 'unknown')
            return create_invoice_api
        except Exception as e:
            message = "An exception occurred with Now create_crypto_invoice: " + str(e)
            _logger.exception(message)
            return {"code": message}

    def check_payment_status_payment_link(self, args):
        try:
            _logger.info(f"Called Now check_payment_status_payment_link. Passed args are {args}")
            cryptopay_pm = self.env['pos.payment.method'].search([('id', '=', args['pm_id'])], limit=1)
            if cryptopay_pm.use_payment_terminal != 'now':
                return super().check_payment_status(args)
            invoice_status_api = cryptopay_pm.call_cryptopay_api({}, '/v1/payment/?limit=10&page=0&sortBy=created_at&orderBy=desc', 'GET', 1)
            if invoice_status_api.status_code != 200:
                payment_to_return = {'payment_status': 'inaccessible'}
                return payment_to_return
            resJson = invoice_status_api.json()['data']
            payment_to_return = {'payment_status': 'not_found'}
            for payment in resJson:
                if payment.get('order_id') == args['order_id']:
                    payment_to_return = payment
                    break
            _logger.info(f"Completed Now check_payment_status_payment_link. Passing back {payment_to_return}")
            return payment_to_return
        except Exception as e:
            message = "An exception occurred with Now check_payment_status_payment_link: " + str(e)
            _logger.exception(message)
            return {"payment_status": message}
    def check_payment_status_direct_invoice(self, args):
        try:
            _logger.info(f"Called Now check_payment_status_direct_invoice. Passed args are {args}")
            cryptopay_pm = self.env['pos.payment.method'].search([('id', '=', args['pm_id'])], limit=1)
            if cryptopay_pm.use_payment_terminal != 'now':
                return super().check_payment_status(args)
            invoice_status_api = cryptopay_pm.call_cryptopay_api({}, '/v1/payment/' + args.get('invoice_id'), 'GET')
            if invoice_status_api.status_code != 200:
                return {"payment_status": "inaccessible"}
            _logger.info(f"Completed Now check_payment_status_payment_link. Passing back {invoice_status_api.json()}")
            return invoice_status_api.json()
        except Exception as e:
            message = "An exception occurred with Now check_payment_status_direct_invoice: " + str(e)
            _logger.exception(message)
            return {"payment_status": message}

    @api.model 
    def now_check_payment_status(self, args):
        try:
            _logger.info("NowPayments status check requested for order_id=%s invoice_id=%s", args.get('order_id'), args.get('invoice_id'))
            cryptopay_pm = self.env['pos.payment.method'].search([('id', '=', args['pm_id'])], limit=1)
            if cryptopay_pm.use_payment_terminal != 'now':
                return super().check_payment_status(args)
            if cryptopay_pm.now_payment_flow == 'direct invoice':
                check_payment_api = cryptopay_pm.check_payment_status_direct_invoice(args)
                _logger.info("NowPayments status check result for order_id=%s status=%s", args.get('order_id'), check_payment_api.get('payment_status') if isinstance(check_payment_api, dict) else 'unknown')
                return check_payment_api
            else:
                check_payment_api = cryptopay_pm.check_payment_status_payment_link(args)
                _logger.info("NowPayments status check result for order_id=%s status=%s", args.get('order_id'), check_payment_api.get('payment_status') if isinstance(check_payment_api, dict) else 'unknown')
                return check_payment_api
        except Exception as e:
            message = "An exception occurred with Now now_check_payment_status: " + str(e)
            _logger.exception(message)
            return {"payment_status": message}

