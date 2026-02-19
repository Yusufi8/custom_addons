# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


# =====================================================
# SALE ORDER
# =====================================================

class SaleOrder(models.Model):
    _inherit = "sale.order"

    customids_ids = fields.One2many(
        "stock.operation.customids",
        "sale_order_id",
        string="Customs IDs"
    )

    # -------------------------------------------------
    # BLOCK CONFIRM IF CAR RULES NOT SATISFIED
    # -------------------------------------------------
    def action_confirm(self):
        for order in self:
            for line in order.order_line:

                if not line.product_id.is_car:
                    continue

                if not line.lot_ids:
                    raise ValidationError(
                        f"Serial Number required for '{line.product_id.display_name}'."
                    )

                if line.product_uom_qty != len(line.lot_ids):
                    raise ValidationError(
                        "Quantity must match number of serial numbers."
                    )

                missing = line.lot_ids.filtered(lambda l: not l.custom_id)
                if missing:
                    names = ", ".join(missing.mapped("name"))
                    raise ValidationError(
                        f"Serial(s) without Customs ID:\n{names}"
                    )

        return super().action_confirm()

    @api.constrains('product_id', 'order_id')
    def _check_duplicate_car_product(self):
        for line in self:
            if not line.product_id.is_car:
                continue

            duplicate = self.search([
                ('order_id', '=', line.order_id.id),
                ('product_id', '=', line.product_id.id),
                ('id', '!=', line.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    f"Car product '{line.product_id.display_name}' "
                    f"cannot be added twice in the same Sale Order."
                )



# # models/website_employee.py
# from odoo import models, fields, api
# from odoo.exceptions import ValidationError
#
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     # Link back to operations
#     customids_ids = fields.One2many('stock.operation.customids', 'sale_order_id', string='Customs IDs')
#
#
# class SaleOrderLine(models.Model):
#     _inherit = "sale.order.line"
#
#     # Add lot_ids field only visible for car products
#     lot_ids = fields.Many2many(
#         "stock.lot",
#         "sale_order_line_lot_rel",
#         "line_id",
#         "lot_id",
#         string="Serial Numbers",
#         domain="[('product_id', '=', product_id)]",
#         help="Select serial numbers for this car"
#     )
#
#     # Auto-show/hide lot_ids based on is_car
#     @api.onchange("product_id")
#     def _onchange_product_id_lots(self):
#         if self.product_id and self.product_id.is_car:
#             return {'domain': {'lot_ids': [('product_id', '=', self.product_id.id)]}}
#         else:
#             self.lot_ids = False
#             return {'domain': {'lot_ids': []}}
#
#     @api.onchange("lot_ids")
#     def _onchange_lot_ids_no_duplicate(self):
#         for line in self:
#             if not line.order_id or not line.lot_ids:
#                 continue
#             other_lots = line.order_id.order_line.filtered(
#                 lambda l: l.id != line.id
#             ).mapped("lot_ids")
#             dup = line.lot_ids & other_lots
#             if dup:
#                 names = ", ".join(dup.mapped("name"))
#                 raise ValidationError(
#                     f"Serial number(s) already selected on another line: {names}."
#                 )
#
#     # MAIN VALIDATION — ONLY ON SALE ORDER
#     @api.constrains("lot_ids", "product_id", "product_uom_qty")
#     def _check_car_lot_and_custom_id(self):
#         for line in self:
#             # Only apply to car products
#             if not line.product_id or not line.product_id.is_car:
#                 continue
#
#             # 1. Lot is mandatory
#             if not line.lot_ids:
#                 raise ValidationError("Serial Number is required for car products.")
#
#             # 2. Quantity must match number of lots
#             if len(line.lot_ids) != int(line.product_uom_qty):
#                 raise ValidationError(
#                     f"You selected {len(line.lot_ids)} serial number(s) but quantity is {line.product_uom_qty}."
#                 )
#
#             # 3. Each lot must have Customs ID
#             missing_custom = line.lot_ids.filtered(lambda l: not l.custom_id)
#             if missing_custom:
#                 names = ", ".join(missing_custom.mapped("name"))
#                 raise ValidationError(
#                     f"The following serial numbers do not have a Customs ID:\n{names}\n"
#                     "Please complete Customs ID operation before selling."
#                 )
#
#             # 4. Same lot cannot be used in another Sale Order (not draft/cancel)
#             for lot in line.lot_ids:
#                 duplicate = self.search([
#                     ("id", "!=", line.id),
#                     ("lot_ids", "=", lot.id),
#                     ("state", "not in", ("draft", "cancel")),
#                 ], limit=1)
#                 if duplicate:
#                     # find related sale order
#                     so = duplicate.order_id if hasattr(duplicate, 'order_id') else None
#                     so_name = so.name if so else 'another order'
#                     raise ValidationError(
#                         f"Serial number {lot.name} is already used in Sale Order {so_name}."
#                     )
