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
    'depends': ['purchase','stock','sale','hr','mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/por.xml',
    ],
    'installable': True,
    'application': False,
    'sequence': -1
}
