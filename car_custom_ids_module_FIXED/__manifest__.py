{
    "name": "Car Custom IDs Workflow",
    "version": "18.0.1.0.0",
    "depends": ["stock", "purchase", "sale", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/inherit_stock_custom.xml",
        "views/inherit_product_template.xml",
        "views/inherit_sale_order.xml",
        "views/inherit_purchase_order.xml",
    ],
    "installable": True,
    "sequence": -100,
}