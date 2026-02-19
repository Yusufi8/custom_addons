from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # User selects multiple lots here
    lot_ids = fields.Many2many(
        "stock.lot",
        "sale_order_line_lot_rel",
        "line_id",
        "lot_id",
        string="Lots",
        domain="[('product_id', '=', product_id)]",
    )

    # -----------------------------------------
    # CREATE → Split into separate lines
    # -----------------------------------------
    @api.model
    def create(self, vals):
        lot_cmd = vals.get("lot_ids")

        # No lot selection → normal behavior
        if not lot_cmd:
            return super().create(vals)

        # Extract lot IDs → only supports (6,0,[...])
        if isinstance(lot_cmd, list) and lot_cmd[0][0] == 6:
            lot_ids = lot_cmd[0][2]
        else:
            return super().create(vals)

        # Only 1 lot → normal create
        if len(lot_ids) <= 1:
            return super().create(vals)

        # MULTIPLE LOTS → SPLIT
        result = self.env["sale.order.line"]
        for lot in lot_ids:
            line_vals = vals.copy()
            line_vals["product_uom_qty"] = 1
            line_vals["lot_ids"] = [(6, 0, [lot])]
            result |= super().create(line_vals)

        return result

    # -----------------------------------------
    # WRITE → Also split into single-lot lines
    # -----------------------------------------
    def write(self, vals):
        lot_cmd = vals.get("lot_ids")
        if not lot_cmd:
            return super().write(vals)

        for line in self:
            # Extract lot list
            if isinstance(lot_cmd, list) and lot_cmd[0][0] == 6:
                lot_ids = lot_cmd[0][2]
            else:
                return super().write(vals)

            # Only 1 → normal update
            if len(lot_ids) <= 1:
                super(SaleOrderLine, line).write(vals)
                continue

            # MULTIPLE LOTS → SPLIT
            base = {
                "order_id": line.order_id.id,
                "product_id": line.product_id.id,
                "price_unit": line.price_unit,
                "name": line.name,
                "product_uom": line.product_uom.id,
            }

            # Remove original line
            line.unlink()

            # Create new lines
            for lot in lot_ids:
                new_vals = base.copy()
                new_vals["product_uom_qty"] = 1
                new_vals["lot_ids"] = [(6, 0, [lot])]
                self.create(new_vals)

        return True


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Lines with exactly ONE lot (1 line = 1 lot)
    lot_visible_lines = fields.One2many(
        "sale.order.line",
        "order_id",
        compute="_compute_lot_visible_lines",
        store=False,
    )

    @api.depends("order_line.lot_ids")
    def _compute_lot_visible_lines(self):
        for order in self:
            order.lot_visible_lines = order.order_line.filtered(
                lambda l: l.lot_ids and len(l.lot_ids) == 1
            )
