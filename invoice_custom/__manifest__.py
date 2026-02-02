{
    'name': 'Invoice Custom',
    'version': '1.0',
    'depends': ['account', 'hospital_yk'],
    'author': 'Yusuf Khan',
    'category': 'Accounting',
    'description': 'Customizations for Invoices',
    'data': [
        'security/ir.model.access.csv',
        'views/inherit_invoice_views.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence':
        -11,
}