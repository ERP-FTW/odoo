# pos_cardpointe_poc

Minimal Odoo 18 proof-of-concept addon to run a POS card-present sale on a CardPointe Integrated Terminal (Clover Flex) through server-side proxy routes.

## What this POC does

- Adds payment terminal option `CardPointe POC` on POS payment methods.
- Adds CardPointe terminal configuration model (`pos.cardpointe.terminal.config`).
- Sends sale request from POS to Odoo JSON controller, then Odoo calls CardPointe terminal API.
- Polls terminal status every second from POS.
- On approval, stores safe metadata on payment line/payment record:
  - `cardpointe_retref`
  - `cardpointe_authcode`
  - `cardpointe_status`
  - optional card brand/last4 (if returned)

No PAN is stored.

## Setup

1. Place module in addons path and update app list.
2. Install module **POS CardPointe POC**.
3. Go to **Point of Sale > Configuration > CardPointe Terminal Configs** and create config:
   - Base URL: `https://bolt-terminal-uat.cardpointe.com`
   - Port: `443`
   - Merchant ID: `800000009875`
   - Device Type: `Clover Flex`
   - Device Serial: optional (`C0...`)
4. Open or create POS payment method named `Card (CardPointe POC)`:
   - Set **Use a Payment Terminal** = `CardPointe POC`
   - Set **CardPointe Config** = your config
5. Ensure method is enabled on your POS configuration.

## Testing checklist

1. Open POS session.
2. Add product and go to payment.
3. Select `Card (CardPointe POC)`.
4. Click **Send Payment Request** (terminal action button on payment line).
5. Complete tap/insert/swipe on Clover Flex.
6. Confirm POS shows done or error.
7. Validate order.
8. Check `pos.payment` record has `cardpointe_retref` and `cardpointe_authcode` for approved payment.

## Notes

- POC only: no refund/void/tip/split/offline flow.
- Uses polling endpoint (`/pos_cardpointe_poc/poll`).
- Secrets stay server-side in Odoo models; browser only sends IDs and transaction values.
