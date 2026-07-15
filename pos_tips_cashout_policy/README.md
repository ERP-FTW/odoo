# POS Tips Cashout Policy

Extends `pos_tip_cashout_direct` with tip-out / tip-pool policies. The existing POS cashout screen remains in use, but its card-tip remaining amount becomes policy-adjusted when an active policy applies.

## Configuration

1. Keep Odoo POS tips configured with `pos.config.tip_product_id`; this module does not replace native tip products or recreate tip revenue.
2. Create a **Tip Policy** and select the company/POS configurations, effective dates, journal, and Tips Payable account.
3. Add policy lines with a contribution percent, optional source employees, recipient employees, and optional distribution percentage.
4. Create a **Tip Pool Batch** for a POS session, calculate it, and create the draft journal entry. The journal entry is never posted automatically.

## Cashout math

When no policy applies, Module 1 behavior is unchanged.

When a policy applies, employee drawer payout availability is:

`gross card tips - policy contribution + policy distribution - prior drawer payouts = net available`

If the policy requires calculation before cashout, the POS blocks drawer payout until a calculated batch exists. If session cashout is disabled on the policy, the screen shows the net liability but disables drawer payout.

## Accounting

The draft journal entry reclassifies existing Tips Payable liability by debiting source employee contribution lines and crediting recipient employee distribution lines. It does not duplicate the original Odoo POS tip product accounting.
