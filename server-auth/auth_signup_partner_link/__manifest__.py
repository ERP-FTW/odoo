{
    "name": "Auth Signup Partner Link",
    "summary": "Block duplicate signup users and optionally link signup to existing contacts",
    "category": "Technical Settings",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["auth_signup", "portal", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/signup_partner_link_event_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
}
