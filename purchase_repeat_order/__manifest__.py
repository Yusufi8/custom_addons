{
    'name': 'Purchase Repeat Order',
    'version': '1.0',
    'category': 'Purchase',
    'summary': 'Repeat Purchase Orders with RO button',
    'description': """
Create repeated Purchase Orders with the same data.
Adds RO button, Close button, and Smart Button to track repeated orders.
""",
    'author': 'Yusuf',
    'depends': ['purchase', 'stock', 'sale', 'hr', 'account', 'mail','base'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/cron.xml',
        'data/email_template.xml',
        'views/por.xml',
        'views/subscription_order.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'sequence': -1
}
