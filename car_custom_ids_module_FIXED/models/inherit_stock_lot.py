from odoo import models, fields


class StockLot(models.Model):
    _inherit = "stock.lot"

    custom_id = fields.Char("Customs ID", copy=False, index=True)

    _sql_constraints = [
        ("custom_id_uniq", "unique(custom_id, company_id)", "Customs ID must be unique per company!")
    ]