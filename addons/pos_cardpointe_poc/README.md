# pos_cardpointe_poc

Minimal Odoo 16 proof-of-concept addon to run POS card-present sales on CardPointe Bolt terminals (Clover Flex) through server-side proxy calls.

## Flow used by this module

1. `POST /v2/connect`
   - Body: `merchantId`, `hsn`
   - Header: `Authorization: <auth_key>`
   - Reads `X-CardConnect-SessionKey` response header.
2. `POST /v4/authCard`
   - Body: `merchantId`, `hsn`, `amount` (implied cents), `capture: true`, `orderId`
   - Headers: `Authorization` + `X-CardConnect-SessionKey`

No PAN is stored.

## Configuration

Create **Point of Sale > Configuration > CardPointe Terminal Configs**:

- Base URL: `https://bolt-uat.cardpointe.com/api`
- Auth Key: CardPointe Bolt authorization key
- Merchant ID: `800000009875`
- HSN: `C047UG43720996`
- Request Timeout Seconds: `120`

Then configure payment method `Card (CardPointe POC)`:

- Use a Payment Terminal: `CardPointe POC`
- CardPointe Config: your config record

## What is persisted on payment

- `cardpointe_retref`
- `cardpointe_authcode`
- `cardpointe_respcode`
- `cardpointe_resptext`
- `cardpointe_token` (if returned)
- `cardpointe_status`

## Troubleshooting

- **401 Unauthorized**: wrong/missing `auth_key`.
- **errorCode 9 / merchant mode**: terminal is in Merchant Mode, switch to CardPointe Integrated/Bolt app.
- **errorCode 8 / cancelled**: payment cancelled on terminal.
- **timeout**: terminal or network did not finish within timeout; verify terminal app mode, connectivity, and retry.

## Test checklist

1. Create terminal config:
   - `base_url = https://bolt-uat.cardpointe.com/api`
   - `auth_key = <provided>`
   - `merchant_id = 800000009875`
   - `hsn = C047UG43720996`
2. Link payment method **Card (CardPointe POC)** to this config.
3. Open POS, create order `$1.00`, click **Send Payment Request**.
4. Confirm terminal prompts for card (if not in merchant mode).
5. Confirm approved payment stores `retref/authcode/respcode/resptext` on `pos.payment`.


## Sanity checklist

- Module dependency: install `payment_cardpointe_base` before/with this addon.
- `POST /v2/connect` must return `X-CardConnect-SessionKey`.
- `POST /v4/authCard` must return `respstat/respcode`; approvals accept `respstat=A` or `respcode in {000,00}`.
- Ensure Authorization and session key are always redacted in logs.
