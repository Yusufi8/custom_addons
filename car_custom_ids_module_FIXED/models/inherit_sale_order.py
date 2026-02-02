# models/website_employee.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Link back to operations
    customids_ids = fields.One2many('stock.operation.customids', 'sale_order_id', string='Customs IDs')


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Add lot_ids field only visible for car products
    lot_ids = fields.Many2many(
        "stock.lot",
        "sale_order_line_lot_rel",
        "line_id",
        "lot_id",
        string="Serial Numbers",
        domain="[('product_id', '=', product_id)]",
        help="Select serial numbers for this car"
    )

    # Auto-show/hide lot_ids based on is_car
    @api.onchange("product_id")
    def _onchange_product_id_lots(self):
        if self.product_id and self.product_id.is_car:
            return {'domain': {'lot_ids': [('product_id', '=', self.product_id.id)]}}
        else:
            self.lot_ids = False
            return {'domain': {'lot_ids': []}}

    # MAIN VALIDATION — ONLY ON SALE ORDER
    @api.constrains("lot_ids", "product_id", "product_uom_qty")
    def _check_car_lot_and_custom_id(self):
        for line in self:
            # Only apply to car products
            if not line.product_id or not line.product_id.is_car:
                continue

            # 1. Lot is mandatory
            if not line.lot_ids:
                raise ValidationError("Serial Number is required for car products.")

            # 2. Quantity must match number of lots
            if len(line.lot_ids) != int(line.product_uom_qty):
                raise ValidationError(
                    f"You selected {len(line.lot_ids)} serial number(s) but quantity is {line.product_uom_qty}."
                )

            # 3. Each lot must have Customs ID
            missing_custom = line.lot_ids.filtered(lambda l: not l.custom_id)
            if missing_custom:
                names = ", ".join(missing_custom.mapped("name"))
                raise ValidationError(
                    f"The following serial numbers do not have a Customs ID:\n{names}\n"
                    "Please complete Customs ID operation before selling."
                )

            # 4. Same lot cannot be used in another Sale Order (not draft/cancel)
            for lot in line.lot_ids:
                duplicate = self.search([
                    ("id", "!=", line.id),
                    ("lot_ids", "=", lot.id),
                    ("state", "not in", ("draft", "cancel")),
                ], limit=1)
                if duplicate:
                    # find related sale order
                    so = duplicate.order_id if hasattr(duplicate, 'order_id') else None
                    so_name = so.name if so else 'another order'
                    raise ValidationError(
                        f"Serial number {lot.name} is already used in Sale Order {so_name}."
                    )