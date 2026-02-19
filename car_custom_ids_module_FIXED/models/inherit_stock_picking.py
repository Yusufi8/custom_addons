# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        self._check_sale_order_lots_match()
        return super().button_validate()

    def _check_sale_order_lots_match(self):
        for picking in self:
            sale = picking.sale_id
            if not sale:
                continue

            sale_lines = sale.order_line.filtered(
                lambda l: l.product_id.is_car and l.lot_ids
            )
            if not sale_lines:
                continue

            used_by_line = defaultdict(set)
            move_lines = picking.move_line_ids.filtered(
                lambda ml: ml.lot_id and ml.move_id.sale_line_id
            )
            for ml in move_lines:
                sale_line = ml.move_id.sale_line_id
                if sale_line in sale_lines:
                    used_by_line[sale_line.id].add(ml.lot_id.id)

            for line in sale_lines:
                if not line.move_ids.filtered(lambda m: m.picking_id == picking):
                    continue
                selected = set(line.lot_ids.ids)
                used = used_by_line.get(line.id, set())
                missing = selected - used
                extra = used - selected
                if missing or extra:
                    msg = (
                        "Delivery lots for %s must match selected lots on the Sale Order."
                        % line.product_id.display_name
                    )
                    if missing:
                        missing_names = ", ".join(
                            self.env["stock.lot"].browse(list(missing)).mapped("name")
                        )
                        msg += "\nMissing: %s" % missing_names
                    if extra:
                        extra_names = ", ".join(
                            self.env["stock.lot"].browse(list(extra)).mapped("name")
                        )
                        msg += "\nExtra: %s" % extra_names
                    raise ValidationError(msg)
