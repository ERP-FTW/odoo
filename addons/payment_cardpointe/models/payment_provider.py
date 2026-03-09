# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.addons.payment import setup_provider

_logger = logging.getLogger(__name__)

# TODO: Confirm exact Gateway endpoint names in current CardPointe docs.
ENDPOINT_PROFILE_CREATE = None
ENDPOINT_PROFILE_GET = None
ENDPOINT_PROFILE_DELETE = None

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _register_hook(self):
        """Ensure CardPointe provider setup exists on upgrades."""
        res = super()._register_hook()
        try:
            setup_provider(self.env.cr, self.env.registry, 'cardpointe')
        except Exception:
            _logger.exception('[CARDPOINTE] Failed to setup provider during registry hook.')
        return res

    @api.model
    def _setup_provider(self, code):
        """Ensure CardPointe payment method/lines exist so journal can be persisted."""
        res = super()._setup_provider(code)
        if code != 'cardpointe':
            return res

        payment_method = self.env['account.payment.method'].search([('code', '=', code)], limit=1)
        if not payment_method:
            payment_method = self.env['account.payment.method'].sudo().create({
                'name': _('Cardpointe'),
                'code': code,
                'payment_type': 'inbound',
            })

        providers = self.search([('code', '=', code)])
        for provider in providers:
            if provider.journal_id:
                provider._ensure_payment_method_line(allow_create=True)
            else:
                provider._ensure_payment_method_line(allow_create=False)
        return res

    @api.depends('code')
    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'cardpointe').update({
            'support_manual_capture': False,
            'support_refund': False,
            'support_tokenization': True,
        })

    def _cardpointe_create_profile_from_token(self, token, partner, meta=None, consent=False):
        """Create a reusable CardPointe profile from a hosted iFrame token.

        This helper is designed for payment.token flows in recent Odoo versions while remaining
        safe for older integration patterns. Never send or log PAN/CVV; only hosted tokens are
        accepted and only token last4 may be logged.
        """
        self.ensure_one()
        if self.code != 'cardpointe':
            raise UserError(_("CardPointe: invalid payment provider."))
        if not ENDPOINT_PROFILE_CREATE:
            raise UserError(_(
                "CardPointe: profile create endpoint is not configured. "
                "Set ENDPOINT_PROFILE_CREATE according to provider docs."
            ))
        if not token:
            raise UserError(_("CardPointe: missing hosted token for profile creation."))

        if isinstance(partner, models.BaseModel):
            partner = partner[:1]
        else:
            partner = self.env['res.partner'].browse(partner).exists()[:1]
        if not partner:
            raise UserError(_("CardPointe: missing partner for profile creation."))

        payload = {
            'merchid': self.cardpointe_mid,
            'account': token,
            'profile': {
                'name': partner.name,
                'email': partner.email,
                'phone': partner.phone,
                'address': partner.street,
                'city': partner.city,
                'region': partner.state_id.code,
                'country': partner.country_id.code,
                'postal': partner.zip,
            },
            'meta': meta or {},
            'consent': bool(consent),
        }
        payload['profile'] = {k: v for k, v in payload['profile'].items() if v}
        payload = {k: v for k, v in payload.items() if v not in (None, {}, [])}

        _logger.info(
            "[CARDPOINTE] profile create request provider_id=%s partner_id=%s token_last4=%s consent=%s",
            self.id,
            partner.id,
            token[-4:] if isinstance(token, str) else '****',
            bool(consent),
        )
        response = self.with_context(cardpointe_partner_id=partner.id)._cardpointe_request(
            'POST', ENDPOINT_PROFILE_CREATE, payload=payload
        )
        if not response.get('ok'):
            _logger.info(
                "[CARDPOINTE] profile create failure provider_id=%s partner_id=%s correlation_id=%s http_status=%s code=%s",
                self.id,
                partner.id,
                response.get('correlation_id'),
                response.get('http_status'),
                response.get('error_code'),
            )
            return {
                'ok': False,
                'error_code': response.get('error_code'),
                'error_message': response.get('error_message'),
                'raw': response.get('data') or {},
            }

        normalized = self._cardpointe_normalize_profile_data(response.get('data') or {}, token=token)
        return {'ok': True, 'data': normalized, 'raw': response.get('data') or {}}

    def _cardpointe_get_profile(self, profile_id, account_id=None):
        """Fetch an existing CardPointe profile and normalize profile/card details."""
        self.ensure_one()
        if self.code != 'cardpointe':
            raise UserError(_("CardPointe: invalid payment provider."))
        if not ENDPOINT_PROFILE_GET:
            raise UserError(_(
                "CardPointe: profile get endpoint is not configured. "
                "Set ENDPOINT_PROFILE_GET according to provider docs."
            ))
        if not profile_id:
            raise UserError(_("CardPointe: missing profile id."))

        payload = {'profileid': profile_id}
        if account_id:
            payload['accountid'] = account_id
        response = self._cardpointe_request('GET', ENDPOINT_PROFILE_GET, payload=payload)
        if not response.get('ok'):
            return {
                'ok': False,
                'error_code': response.get('error_code'),
                'error_message': response.get('error_message'),
                'raw': response.get('data') or {},
            }
        normalized = self._cardpointe_normalize_profile_data(response.get('data') or {})
        return {'ok': True, 'data': normalized, 'raw': response.get('data') or {}}

    def _cardpointe_delete_profile(self, profile_id, account_id=None):
        """Delete a CardPointe profile or profile account without exposing card details."""
        self.ensure_one()
        if self.code != 'cardpointe':
            raise UserError(_("CardPointe: invalid payment provider."))
        if not ENDPOINT_PROFILE_DELETE:
            raise UserError(_(
                "CardPointe: profile delete endpoint is not configured. "
                "Set ENDPOINT_PROFILE_DELETE according to provider docs."
            ))
        if not profile_id:
            raise UserError(_("CardPointe: missing profile id."))

        payload = {'profileid': profile_id}
        if account_id:
            payload['accountid'] = account_id
        response = self._cardpointe_request('POST', ENDPOINT_PROFILE_DELETE, payload=payload)
        return {
            'ok': bool(response.get('ok')),
            'error_code': response.get('error_code'),
            'error_message': response.get('error_message'),
            'raw': response.get('data') or {},
        }

    def _cardpointe_normalize_profile_data(self, payload, token=None):
        """Normalize CardPointe profile API payloads to payment.token-friendly card fields."""
        data = payload if isinstance(payload, dict) else {}
        expiry_month, expiry_year = self._cardpointe_parse_expiry(
            data.get('expiry') or data.get('exp') or data.get('expiration') or ''
        )
        last4 = (
            data.get('last4')
            or data.get('acctlastfour')
            or data.get('account_last4')
            or self._cardpointe_extract_last4(data.get('account'))
            or (token[-4:] if isinstance(token, str) else None)
        )
        return {
            'profile_id': data.get('profile_id') or data.get('profileid') or data.get('profile'),
            'account_id': data.get('account_id') or data.get('accountid') or data.get('acctid'),
            'last4': last4,
            'brand': data.get('brand') or data.get('cardtype') or data.get('accttype'),
            'expiry_month': expiry_month,
            'expiry_year': expiry_year,
        }

    def _cardpointe_parse_expiry(self, value):
        """Parse flexible CardPointe expiry strings into month/year integers."""
        raw = re.sub(r'\D', '', (value or '').strip())
        if len(raw) < 4:
            return None, None
        month = int(raw[:2])
        year = int(raw[2:6]) if len(raw) >= 6 else int(raw[2:4]) + 2000
        if month < 1 or month > 12:
            return None, None
        return month, year

    def _cardpointe_extract_last4(self, value):
        """Extract the last4 digits from masked card/account strings."""
        digits = re.sub(r'\D', '', value or '')
        return digits[-4:] if len(digits) >= 4 else None
