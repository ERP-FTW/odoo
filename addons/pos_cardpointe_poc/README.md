# pos_cardpointe_poc

Minimal Odoo 18 proof-of-concept addon to run POS card-present sales on CardPointe Bolt terminals (Clover Flex) through server-side proxy calls.

## Flow used by this module

1. `POST /v2/connect`
   - Body: `merchantId`, `hsn`
   - Header: `Authorization: <auth_key>`
   - Reads `X-CardConnect-SessionKey` response header.
2. `POST /v4/authCard`
   - Body: `merchantId`, `hsn`, `amount` (implied cents), `capture: true`, `orderId`, `includeSignature`
   - Headers: `Authorization` + `X-CardConnect-SessionKey`
3. `POST /v2/readSignature` (when signature policy requires post-auth capture)
   - Body: `merchantId`, `hsn`
   - Headers: `Authorization` + `X-CardConnect-SessionKey`
4. `POST /cardconnect/rest/sigcap` (gateway attach)
   - Body: `merchid`, `retref`, `signature`
   - Auth: gateway username/password
5. `POST /v2/cancel` (when cashier clicks **Cancel** while terminal is waiting)
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
- Signature Mode:
  - `never`
  - `msr_over_threshold` (default)
  - `always`
- Signature Threshold Amount: `50.00` (default)
- Signature Capture Method:
  - `inline_authcard` (default)
  - `post_readSignature`

Then configure payment method `Card (CardPointe POC)`:

- Use a Payment Terminal: `CardPointe POC`
- CardPointe Config: your config record

## Signature policy behavior

- Default `authCard` behavior uses `includeSignature=false`.
- Inline capture sends `includeSignature=true` only when policy requires inline signature pre-auth (always mode).
- For `msr_over_threshold`, the module determines swipe/MSR vs EMV using `entrymode` and presence of `emvTagData` from `authCard` response.
- If policy requires signature and method is `post_readSignature`, the module:
  1. Runs `authCard` with `includeSignature=false`
  2. Calls terminal `readSignature`
  3. Calls gateway `sigcap` with original `retref`
- Database persistence stores only booleans:
  - `cardpointe_signature_required`
  - `cardpointe_signature_captured`

## Terminal verification (manual)

### 1) Connect (verify session key)

```bash
BOLT_BASE="https://bolt-uat.cardpointe.com/api"
AUTH_KEY="<bolt_auth_key>"
MID="800000009875"
HSN="C047UG43720996"

curl -sv -X POST "$BOLT_BASE/v2/connect" \
  -H "Authorization: $AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"merchantId\":\"$MID\",\"hsn\":\"$HSN\"}"
```

Confirm `X-CardConnect-SessionKey` exists in response headers.

### 2) authCard (baseline includeSignature=false)

```bash
SESSION_KEY="<session_key_from_connect>"
ORDER_ID="POS-TEST-1001"
AMT_CENTS="100"

curl -sv -X POST "$BOLT_BASE/v4/authCard" \
  -H "Authorization: $AUTH_KEY" \
  -H "X-CardConnect-SessionKey: $SESSION_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"merchantId\":\"$MID\",\"hsn\":\"$HSN\",\"amount\":\"$AMT_CENTS\",\"capture\":true,\"orderId\":\"$ORDER_ID\",\"includeSignature\":false}"
```

### 3) readSignature (post capture path)

```bash
curl -sv -X POST "$BOLT_BASE/v2/readSignature" \
  -H "Authorization: $AUTH_KEY" \
  -H "X-CardConnect-SessionKey: $SESSION_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"merchantId\":\"$MID\",\"hsn\":\"$HSN\"}"
```

### 4) sigcap (attach signature to original retref)

```bash
GW_BASE="https://fts-uat.cardconnect.com/cardconnect/rest"
GW_USER="testing"
GW_PASS="testing123"
RETREF="<retref_from_authCard>"
SIG_B64="<signature_blob_from_readSignature>"

curl -sv -u "$GW_USER:$GW_PASS" \
  -H "Content-Type: application/json" \
  -d "{\"merchid\":\"$MID\",\"retref\":\"$RETREF\",\"signature\":\"$SIG_B64\"}" \
  "$GW_BASE/sigcap"
```

## Test Connect button

Terminal config form includes admin-only **Test Connect** button.

- It calls terminal `connect` using current record settings.
- It reports success/failure in a notification.
- Secret headers/tokens remain redacted in server logs.

## What is persisted on payment

- `cardpointe_retref`
- `cardpointe_authcode`
- `cardpointe_respcode`
- `cardpointe_resptext`
- `cardpointe_token` (if returned)
- `cardpointe_status`
- `cardpointe_signature_required`
- `cardpointe_signature_captured`

## Troubleshooting

- **401 Unauthorized**: wrong/missing `auth_key`.
- **errorCode 9 / merchant mode**: terminal is in Merchant Mode, switch to CardPointe Integrated/Bolt app.
- **errorCode 8 / cancelled**: payment cancelled on terminal.
- **timeout**: terminal or network did not finish within timeout; verify terminal app mode, connectivity, and retry.
- **errorCode 7 / already in use on connect**: treat as stale terminal session state; retry once, then restart CardPointe app on terminal if it persists.
- **Signature not attached**: validate gateway credentials on terminal config's merchant config and confirm `sigcap` returns approval.

## Gateway refund/void flow for POS return orders

When a POS payment line amount is negative, this module triggers a server-side Gateway flow:

1. Find the original sale `retref` values from refunded ticket lines.
2. Allocate refund amount across original sale payments (partial refunds supported).
3. `GET /inquire/{retref}/{merchid}`.
4. If unsettled (`setlstat` indicates not settled or is missing): `POST /void`.
5. Otherwise: `POST /refund` with allocated amount.
6. If refund returns `respcode=28` (`Txn not settled`), the system automatically retries as `POST /void`.

Results are written back to the refund `pos.payment` line (`cardpointe_retref`, `cardpointe_respcode`, `cardpointe_resptext`, `cardpointe_operation`, `cardpointe_original_retref`, `cardpointe_ok`).
