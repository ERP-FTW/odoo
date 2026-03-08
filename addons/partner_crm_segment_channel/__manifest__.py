{
    'name': 'Partner CRM Segment Channel',
    'version': '18.0.1.0.0',
    'summary': 'Partner/Lead segment-channel sync and contact reporting',
    'depends': ['contacts', 'crm'],
    'data': [
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
}
