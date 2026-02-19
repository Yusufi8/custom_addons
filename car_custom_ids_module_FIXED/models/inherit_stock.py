# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    lot_ids = fields.Many2many(
        "stock.lot",
        "sale_order_line_lot_rel",
        "line_id",
        "lot_id",
        string="Lot/Serial",
        domain="[('product_id', '=', product_id)]",
    )

    show_lot_field = fields.Boolean(compute="_compute_lot_visibility")
    require_lot_field = fields.Boolean(compute="_compute_lot_visibility")

    @api.depends("product_id", "product_id.tracking")
    def _compute_lot_visibility(self):
        for line in self:
            tracking = line.product_id.tracking or "none"
            line.show_lot_field = tracking in ("lot", "serial")
            line.require_lot_field = tracking == "serial"

    @api.onchange("product_id")
    def _onchange_product_id_clear_lots(self):
        if self.product_id and self.product_id.tracking not in ("lot", "serial"):
            self.lot_ids = [(5, 0, 0)]

    # -------------------------------------------------
    # CLIENT SIDE: ONLY quantity trimming
    # -------------------------------------------------
    @api.onchange("lot_ids", "product_uom_qty")
    def _onchange_validate_lots(self):
        for line in self:
            if line.product_id.tracking != "serial":
                continue

            qty = int(line.product_uom_qty or 0)
            selected = line.lot_ids.ids

            if len(selected) > qty:
                line.lot_ids = [(6, 0, selected[:qty])]
                return {
                    "warning": {
                        "title": _("Too many lots"),
                        "message": _("Trimmed lots to match quantity (%s).") % qty,
                    }
                }

    # -------------------------------------------------
    # SERVER SIDE: HARD VALIDATION
    # -------------------------------------------------
    @api.constrains("lot_ids", "order_id")
    def _check_lot_rules(self):
        for line in self:
            if not line.order_id or not line.lot_ids:
                continue

            # 1️⃣ Prevent duplicate inside same order
            other_lots = line.order_id.order_line.filtered(
                lambda l: l.id != line.id
            ).mapped("lot_ids")

            duplicates = line.lot_ids & other_lots
            if duplicates:
                names = ", ".join(duplicates.mapped("name"))
                raise ValidationError(
                    _("Lot/Serial already selected on another line: %s") % names
                )

            # 2️⃣ Prevent reuse in ANY active sales
            for lot in line.lot_ids:
                sold_line = self.search([
                    ("id", "!=", line.id),
                    ("lot_ids", "=", lot.id),
                    ("order_id.state", "!=", "cancel"),
                ], limit=1)

                if sold_line:
                    raise ValidationError(
                        _("Serial '%s' already used in Sale Order '%s'.") %
                        (lot.name, sold_line.order_id.name)
                    )

            # # 2️⃣ Prevent reuse in confirmed sales
            # for lot in line.lot_ids:
            #     sold_line = self.search([
            #         ("id", "!=", line.id),
            #         ("lot_ids", "=", lot.id),
            #         ("order_id.state", "in", ("sale", "done")),
            #     ], limit=1)
            #
            #     if sold_line:
            #         raise ValidationError(
            #             _("Serial '%s' already sold in Sale Order '%s'.") %
            #             (lot.name, sold_line.order_id.name)
            #         )







# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError
#
# class SaleOrderLine(models.Model):
#     _inherit = "sale.order.line"
#
#
#     lot_ids = fields.Many2many(
#         "stock.lot",
#         "sale_order_line_lot_rel",
#         "line_id",
#         "lot_id",
#         domain="[('product_id', '=', product_id)]",
#         string="Lot/Serial",
#     )
#
#     show_lot_field = fields.Boolean(compute="_compute_lot_visibility")
#     require_lot_field = fields.Boolean(compute="_compute_lot_visibility")
#
#     @api.depends("product_id", "product_id.tracking")
#     def _compute_lot_visibility(self):
#         for line in self:
#             tracking = line.product_id.tracking or "none"
#             line.show_lot_field = tracking in ("lot", "serial")
#             line.require_lot_field = tracking == "serial"
#
#
#     @api.onchange("product_id")
#     def _onchange_product_id_clear_lots(self):
#         if self.product_id and self.product_id.tracking not in ("lot", "serial"):
#             self.lot_ids = [(5, 0, 0)]
#
#     @api.onchange("lot_ids", "product_uom_qty")
#     def _onchange_validate_lots(self):
#         """Client-side: remove already-used lots, trim excess, show warnings."""
#         for line in self:
#             if not line.product_id or line.product_id.tracking not in ("serial", "lot"):
#                 continue
#
#             qty = int(line.product_uom_qty or 0)
#             selected_ids = list(line.lot_ids.ids)
#
#             # Find lots used in other active sale lines
#             if selected_ids:
#                 other_lines = self.env["sale.order.line"].search([
#                     ("id", "!=", line.id),
#                     ("lot_ids", "in", selected_ids),
#                     ("order_id.state", "!=", "cancel"),
#                 ])
#                 used_ids = [l.id for l in other_lines.mapped("lot_ids") if l.id in selected_ids]
#             else:
#                 used_ids = []
#
#             # Remove used lots automatically
#             if used_ids:
#                 valid_ids = [i for i in selected_ids if i not in used_ids]
#                 line.lot_ids = [(6, 0, valid_ids)]
#                 return {
#                     "warning": {
#                         "title": _("Lot already used"),
#                         "message": _(
#                             "Removed %s because it's already used in another sale."
#                         ) % ", ".join(map(str, used_ids)),
#                     }
#                 }
#
#             # If serial-tracked, enforce the exact number client-side (trim extras)
#             if line.product_id.tracking == "serial":
#                 if qty == 0 and selected_ids:
#                     # nothing to match: clear selection
#                     line.lot_ids = [(5, 0, 0)]
#                     return {
#                         "warning": {
#                             "title": _("Quantity is zero"),
#                             "message": _("Cleared lot selection because quantity is 0."),
#                         }
#                     }
#                 if len(selected_ids) > qty:
#                     # trim to first qty selected
#                     line.lot_ids = [(6, 0, selected_ids[:qty])]
#                     return {
#                         "warning": {
#                             "title": _("Too many lots"),
#                             "message": _("Trimmed lots to match ordered quantity (%s).") % qty,
#                         }
#                     }
#                 if len(selected_ids) < qty:
#                     return {
#                         "warning": {
#                             "title": _("Not enough lots"),
#                             "message": _("Please select exactly %s lot/serial numbers.") % qty,
#                         }
#                     }
#
#     @api.onchange("lot_ids")
#     def _onchange_no_duplicate_lots_in_order(self):
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
#                     _("Lot/Serial already selected on another line: %s") % names
#                 )
#
#     @api.constrains("lot_ids", "order_id")
#     def _check_duplicate_lots_in_order(self):
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
#                     _("Lot/Serial already selected on another line: %s") % names
#                 )
#

