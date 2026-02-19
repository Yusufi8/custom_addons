from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    show_custom_ids_button = fields.Boolean(
        string="Show Customs Button",
        compute="_compute_show_custom_ids_button"
    )

    customids_ids = fields.One2many(
        'stock.operation.customids', 'purchase_order_id', string='Customs IDs'
    )

    customids_status = fields.Selection([
        ('none', 'No Operation'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled')
    ], compute='_compute_customids_status', string='Customs Status', tracking=True)

    @api.depends('customids_ids.status')
    def _compute_customids_status(self):
        for order in self:
            statuses = order.customids_ids.mapped('status')
            if 'confirmed' in statuses:
                order.customids_status = 'confirmed'
            elif 'draft' in statuses:
                order.customids_status = 'draft'
            elif 'canceled' in statuses:
                order.customids_status = 'canceled'
            else:
                order.customids_status = 'none'

    @api.depends("picking_ids.state", "picking_ids.move_line_ids.lot_id")
    def _compute_show_custom_ids_button(self):
        CustomIDs = self.env["stock.operation.customids"]
        for order in self:
            if CustomIDs.search_count([("purchase_order_id", "=", order.id)]):
                order.show_custom_ids_button = False
                continue
            order.show_custom_ids_button = any(
                picking.state == "done" and any(ml.lot_id for ml in picking.move_line_ids)
                for picking in order.picking_ids
            )

    # ✅ MUST BE INSIDE THE CLASS
    def action_receive_customs_id(self):
        self.ensure_one()
        CustomOp = self.env['stock.operation.customids']
        action = self.env.ref('car_custom_ids_module_FIXED.action_customids').read()[0]
        action["context"] = dict(self.env.context, create=False, delete=False, edit=True)
        form_view = self.env.ref('car_custom_ids_module_FIXED.view_customids_form')

        existing_op = CustomOp.search([
            ('purchase_order_id', '=', self.id),
            ('status', '!=', 'cancel')
        ], limit=1)

        if existing_op:
            action.update({
                'res_id': existing_op.id,
                'view_mode': 'form',
                'views': [(form_view.id, 'form')],
                'target': 'current',
            })
            return action

        op = CustomOp.create({
            'partner_id': self.partner_id.id,
            'purchase_order_id': self.id,
            'source_number': self.name,
            'operation_type': 'po',
            'status': 'draft',
        })

        op.create_lines()

        action.update({
            'res_id': op.id,
            'view_mode': 'form',
            'views': [(form_view.id, 'form')],
            'target': 'current',
        })
        return action











# # models/purchase_order.py
# from odoo import models, fields, api
# from odoo.exceptions import ValidationError
#
#
# class PurchaseOrder(models.Model):
#     _inherit = "purchase.order"
#
#     show_custom_ids_button = fields.Boolean(
#         string="Show Customs Button",
#         compute="_compute_show_custom_ids_button"
#     )
#
#
#     # Link back to operations
#     customids_ids = fields.One2many(
#         'stock.operation.customids', 'purchase_order_id', string='Customs IDs'
#     )
#
#     customids_status = fields.Selection([
#         ('none', 'No Operation'),
#         ('draft', 'Draft'),
#         ('confirmed', 'Confirmed'),
#         ('canceled', 'Canceled')
#     ], string='Customs Status', compute='_compute_customids_status', tracking=True)
#
#     @api.depends('customids_ids.status')
#     def _compute_customids_status(self):
#         for order in self:
#             statuses = order.customids_ids.mapped('status')
#             if 'confirmed' in statuses:
#                 order.customids_status = 'confirmed'
#             elif 'draft' in statuses:
#                 order.customids_status = 'draft'
#             elif 'canceled' in statuses:
#                 order.customids_status = 'canceled'
#             else:
#                 order.customids_status = 'none'
#
#     @api.depends("picking_ids.state", "picking_ids.move_line_ids.lot_id")
#     def _compute_show_custom_ids_button(self):
#         CustomIDs = self.env["stock.operation.customids"]
#         for order in self:
#             # Hide if one already exists for this purchase order
#             if CustomIDs.search_count([("purchase_order_id", "=", order.id)]):
#                 order.show_custom_ids_button = False
#                 continue
#             # Show only if any receipt is done and has serial numbers
#             order.show_custom_ids_button = any(
#                 picking.state == "done" and any(ml.lot_id for ml in picking.move_line_ids)
#                 for picking in order.picking_ids
#             )
#
#     # def action_receive_customs_id(self):
#     #     self.ensure_one()
#     #
#     #     if not any(self.order_line.mapped("product_id.is_car")):
#     #         raise ValidationError("No car products in this Purchase Order.")
#     #
#     #     # If an operation already exists for this purchase order, open the latest one
#     #     existing_ops = self.customids_ids.filtered(lambda op: op.purchase_order_id and op.purchase_order_id.id == self.id)
#     #     if existing_ops:
#     #         # prefer draft or latest
#     #         op = existing_ops.sorted(key=lambda r: r.id, reverse=True)[0]
#     #         return {
#     #             "type": "ir.actions.act_window",
#     #             "name": "Customs ID",
#     #             "res_model": "stock.operation.customids",
#     #             "res_id": op.id,
#     #             "view_mode": "form",
#     #             "target": "self",
#     #         }
#     #
#     #     vals = {
#     #         "partner_id": self.partner_id.id if self.partner_id else False,
#     #         "purchase_order_id": self.id,
#     #         "sale_purchase_reference": self.name,
#     #         "operation_type": 'po',
#     #         "date": fields.Date.context_today(self),
#     #     }
#     #
#     #     operation = self.env["stock.operation.customids"].create([vals])[0]
#     #
#     #     # Auto-load received car lines into the operation
#     #     operation.create_lines()
#     #
#     #     return {
#     #         "type": "ir.actions.act_window",
#     #         "name": "Customs ID",
#     #         "res_model": "stock.operation.customids",
#     #         "res_id": operation.id,
#     #         "view_mode": "form",
#     #         "target": "self",
#     #     }
#
# def action_receive_customs_id(self):
#     self.ensure_one()
#     CustomOp = self.env['stock.operation.customids']
#
#     # 🔒 Check existing Customs ID operation for this PO
#     existing_op = CustomOp.search([
#         ('purchase_order_id', '=', self.id),
#         ('status', '!=', 'cancel')
#     ], limit=1)
#
#     if existing_op:
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Custom IDs',
#             'res_model': 'stock.operation.customids',
#             'res_id': existing_op.id,
#             'view_mode': 'form',
#             'target': 'current',
#         }
#
#     # ✅ Create ONLY if none exists
#     op = CustomOp.create({
#         'partner_id': self.partner_id.id,
#         'purchase_order_id': self.id,
#         'source_number': self.name,
#         'operation_type': 'po',
#         'status': 'draft',
#     })
#
#     op.create_lines()
#
#     return {
#         'type': 'ir.actions.act_window',
#         'name': 'Custom IDs',
#         'res_model': 'stock.operation.customids',
#         'res_id': op.id,
#         'view_mode': 'form',
#         'target': 'current',
#     }
