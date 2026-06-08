Payment Fiserv ACH Outbound
===========================

MVP outbound ACH provider using CardPointe/Fiserv authorization + funding verification.

Flow
----
1. Posted outbound supplier payment calls transaction send hook.
2. Provider sends ACH authorization and stores retref/status on transaction.
3. Transaction stays pending until funding refresh confirms settlement.
4. Funding ACH return codes are captured and mapped to error state.

Notes
-----
* USD-only validation enforced.
* TODO: webhook reconciliation and NACHA-constrained reversal workflow in later versions.
