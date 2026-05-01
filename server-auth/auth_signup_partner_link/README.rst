Auth Signup Partner Link
========================

Purpose
-------

This module improves public signup identity resolution by blocking duplicate users,
optionally linking signups to an existing contact, and recording cases for admin
review.

Settings
--------

* **Enable duplicate user blocking**: blocks signup when an existing user already
  uses the submitted email/login.
* **Enable contact linking**: allows contact matching and policy-based behavior.
* **Link signup to existing contact**:

  * ``never``: never auto-link, continue signup.
  * ``single_match``: link only when exactly one contact matches and it has no user.
  * ``manual``: block and require manual review when any contact matches.

Behavior matrix
---------------

* Existing user + duplicate blocking enabled -> block, event ``existing_user_blocked``.
* Existing user + duplicate blocking disabled -> continue, event ``existing_user_found_not_blocked``.
* Contact linking disabled + matches -> continue, event ``partner_match_linking_disabled``.
* Policy ``never`` + matches -> continue, event ``partner_match_linking_disabled``.
* Policy ``manual`` + matches -> block, event ``partner_manual_review``.
* Policy ``single_match`` + 1 contact no user -> link partner, event ``partner_linked``.
* Policy ``single_match`` + 1 contact with user -> block, event ``partner_has_existing_user``.
* Policy ``single_match`` + multiple contacts -> block, event ``partner_multiple_conflict``.

Admin review location
---------------------

Settings > Technical > Signup Events (admin/system users).

Compatibility with auth_signup_verify_email
-------------------------------------------

No hard dependency is declared. The module injects checks in ``/web/signup``
before delegating to the active signup flow and adds ``partner_id`` into signup
values so that standard signup and passwordless verify-email flows remain
compatible when both modules are installed.

Manual test checklist
---------------------

1. Brand-new email -> signup proceeds; optional ``signup_created_new_partner`` event.
2. Existing portal user -> blocked, ``existing_user_blocked``.
3. Existing internal user -> blocked, ``existing_user_blocked``.
4. One contact without user + single_match -> user created and linked; ``partner_linked``.
5. One contact with user + single_match -> blocked; ``partner_has_existing_user``.
6. Multiple contacts same email + single_match -> blocked; ``partner_multiple_conflict`` with ``partner_ids``.
7. Contact linking disabled -> no auto-link; ``partner_match_linking_disabled`` when contacts exist.
8. Policy manual -> blocked when contacts exist; ``partner_manual_review``.
9. Policy never -> no link; continue unless duplicate-user rule blocks.
10. Duplicate blocking disabled -> ``existing_user_found_not_blocked`` and normal downstream behavior.
