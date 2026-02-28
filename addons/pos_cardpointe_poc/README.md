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
3. `POST /v2/cancel` (when cashier clicks **Cancel** while terminal is waiting)
   - Body: `merchantId`, `hsn`
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
- **errorCode 7 / already in use on connect**: treat as stale terminal session state; retry once, then restart CardPointe app on terminal if it persists.
- **Cancel button appears to do nothing**: ensure multiple Odoo workers are available so a long-running `/auth` request does not starve the `/cancel` request, then verify logs for `CardPointe cancel mapped`.
- **Proactive troubleshooting logs**: track one payment lifecycle by filtering server logs for request id (`CardPointe terminal session established request_id=...`, `CardPointe auth started request_id=...`, `CardPointe cancel ...`).

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


## Gateway refund/void flow for POS return orders

When a POS payment line amount is negative, this module now triggers a server-side Gateway flow:

1. Find the original sale `retref` values from refunded ticket lines.
2. Allocate refund amount across original sale payments (partial refunds supported).
3. `GET /inquire/{retref}/{merchid}`.
4. If unsettled (`setlstat` indicates not settled): `POST /void`.
5. Otherwise: `POST /refund` with allocated amount.

Results are written back to the refund `pos.payment` line (`cardpointe_retref`, `cardpointe_respcode`, `cardpointe_resptext`, `cardpointe_operation`, `cardpointe_original_retref`).

### cURL examples

```bash
GW_USER="testing"
GW_PASS="testing123"
MID="800000009875"
RETREF="343005123105"

curl -sv -u "$GW_USER:$GW_PASS" \
  "https://fts-uat.cardconnect.com/cardconnect/rest/inquire/$RETREF/$MID"
```

```bash
curl -sv -u "$GW_USER:$GW_PASS" \
  -H "Content-Type: application/json" \
  -d '{"merchid":"$MID","retref":"$RETREF"}' \
  "https://fts-uat.cardconnect.com/cardconnect/rest/void"
```

```bash
AMT="1.00"
curl -sv -u "$GW_USER:$GW_PASS" \
  -H "Content-Type: application/json" \
  -d '{"merchid":"$MID","retref":"$RETREF","amount":"$AMT"}' \
  "https://fts-uat.cardconnect.com/cardconnect/rest/refund"
```
