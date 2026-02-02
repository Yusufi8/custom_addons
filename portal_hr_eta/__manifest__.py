{
    "name": "Portal HR – Employees & Time Off",
    "version": "18.0.1.0.0",
    "author": "Yusuf Khan",
    "category": "Human Resources",
    "summary": "Employee directory, personal time off and approvals in the customer portal",
    "depends": [
        "portal",
        "website",
        "hr",
        "hr_holidays",
        "account",
        "mail",
    ],
    "data": [
        # =====================
        # SECURITY
        # =====================
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "security/ir_rule_timeoff.xml",

        # =====================
        # PORTAL HOME (cards & counters)
        # =====================
        "views/portal_home_timeoff.xml",

        # =====================
        # EMPLOYEES (portal)
        # =====================
        "views/website_employees.xml",

        # =====================
        # MY TIME OFF (portal)
        # =====================
        "views/portal_my_timeoff.xml",
        "views/portal_timeoff_create.xml",

        # =====================
        # APPROVALS (portal)
        # =====================
        "views/portal_timeoff_approvals.xml",

        # =====================
        # OPTIONAL / FALLBACK
        # =====================
        "views/portal_error_pages.xml",
        "views/website_home.xml",
    ],
    "installable": True,
    "application": False,
}


# {
#     'name': 'My Account Employee Orders',
#     'version': '1.0',
#     'author': 'Yusuf Khan',
#     'category': 'website',
#     'summary': 'Module to display employees on the website and link to their account orders',
#     'depends': ['portal', 'website', 'hr', 'account', 'hr_holidays'],
#     'data': [
#         'security/ir_rule.xml',
#         'security/ir_rule_timeoff.xml',
#         'security/ir.model.access.csv',
#         'views/website_home.xml',
#         'views/website_employees.xml',
#         'views/portal_home_timeoff.xml',
#         'views/portal_my_timeoff.xml',
#         'views/portal_timeoff_approvals.xml',
#         'views/portal_timeoff_create.xml',
#         'views/portal_error_pages.xml',
#     ],
#     'installable': True,
#     'application': False,
# }