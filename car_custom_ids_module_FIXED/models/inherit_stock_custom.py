# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class StockOperationHead(models.Model):
    _name = 'stock.operation.customids'
    _description = 'Inventory Operation Custom IDs'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "sale_purchase_reference"

    operation_type = fields.Selection([
        ('po', 'Purchase Order'),
        ('so', 'Sale Order'),
    ], string="Operation Type")
    source_number = fields.Char(
        string="Source Document",
        readonly=True,
        tracking=True
    )
    partner_id = fields.Many2one('res.partner', string='Partner')
    purchase_order_id = fields.Many2one('purchase.order', string="Linked Purchase Order")
    sale_order_id = fields.Many2one('sale.order', string="Linked Sales Order")
    date = fields.Date(string="Date")
    sale_purchase_reference = fields.Char(string="Source Number")
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled')
    ], string="Status", default='draft', tracking=True)
    description = fields.Text(string="Description", tracking=True)

    line_ids = fields.One2many('stock.operation.customids.line', 'head_id', string="Operation Lines")

    # attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number')

    # Enables Odoo Messaging Features
    message_follower_ids = fields.One2many('mail.followers', 'res_id', string="Followers")
    message_ids = fields.One2many('mail.message', 'res_id', string="Messages")
    activity_ids = fields.One2many('mail.activity', 'res_id', string="Activities")

    def name_get(self):
        result = []
        for record in self:
            name = record.sale_purchase_reference if record.sale_purchase_reference else f"{record._name}, {record.id}"
            result.append((record.id, name))
        return result

    def action_confirm_operation(self):
        """ Confirms the operation: validate lines and write Customs ID onto lots.
        Validation added:
        - Prevent confirming if the lot already has a different custom_id.
        - Prevent conflicting assignment if another operation for the same purchase already references this lot.
        """
        for record in self:
            missing_ids = record.line_ids.filtered(lambda l: not l.custom_id)
            if missing_ids:
                raise UserError("All lines must have a Customs ID before confirming.")

            for line in record.line_ids:
                if not line.product_id or not line.product_id.is_car:
                    raise ValidationError("Only Car products are allowed in this operation.")

                # Resolve lot from serial if needed
                if not line.lot_id and line.serial_chassis_number:
                    lots = self.env['stock.lot'].search([
                        ('name', '=', line.serial_chassis_number),
                        ('product_id', '=', line.product_id.id)
                    ])
                    if not lots:
                        raise UserError(f"Serial '{line.serial_chassis_number}' not found as a Lot for product {line.product_id.display_name}.")
                    if len(lots) > 1:
                        raise UserError(f"Multiple lots found with serial '{line.serial_chassis_number}' for product {line.product_id.display_name}. Please set the Lot manually.")
                    line.sudo().write({'lot_id': lots[0].id})

                if not line.lot_id:
                    raise ValidationError("Lot is mandatory for each line.")

                # If the lot already has a custom_id, ensure we don't overwrite it with a different one
                if line.lot_id.custom_id:
                    if line.lot_id.custom_id != line.custom_id:
                        raise UserError(
                            f"Lot {line.lot_id.name} already has Customs ID '{line.lot_id.custom_id}'.\n"
                            f"You cannot assign a different Customs ID ('{line.custom_id}') to the same lot."
                        )
                    # If it's identical, no-op for that lot
                    continue

                # Ensure no other operation line for the same purchase references this lot (avoid duplicates across operations)
                if record.purchase_order_id and line.lot_id:
                    dup = self.env['stock.operation.customids.line'].search([
                        ('lot_id', '=', line.lot_id.id),
                        ('head_id.purchase_order_id', '=', record.purchase_order_id.id),
                        ('head_id', '!=', record.id),
                    ], limit=1)
                    if dup:
                        raise UserError(
                            f"Lot {line.lot_id.name} is already present in another Customs operation (ID {dup.head_id.id}) for Purchase Order {record.purchase_order_id.name}."
                            "Please edit the existing operation instead of creating a duplicate."
                        )

                # Write the wizard's Custom ID to the actual Stock Lot (persist it)
                try:
                    line.lot_id.sudo().write({'custom_id': line.custom_id})
                except Exception as e:
                    raise UserError(f"Failed to write Customs ID '{line.custom_id}' to Lot {line.lot_id.name}: {e}")

            # mark operation confirmed
            record.status = 'confirmed'

            # recompute linked orders' computed statuses (safe, will reflect this operation)
            if record.purchase_order_id:
                try:
                    record.purchase_order_id._compute_customids_status()
                except Exception:
                    pass
            if record.sale_order_id:
                try:
                    record.sale_order_id._compute_customids_status()
                except Exception:
                    pass

    def action_confirm_operation(self):
        for record in self:
            if not record.line_ids:
                raise ValidationError("Please add at least one line.")

            for line in record.line_ids:
                if not line.custom_id:
                    raise ValidationError(
                        f"Customs ID missing for {line.product_id.display_name}"
                    )

                if not line.lot_id:
                    raise ValidationError("Lot / Serial is mandatory.")

                # 🚫 Prevent same lot reused in same PO
                duplicate = self.search([
                    ('id', '!=', record.id),
                    ('purchase_order_id', '=', record.purchase_order_id.id),
                    ('line_ids.lot_id', '=', line.lot_id.id),
                    ('status', '=', 'confirmed'),
                ])
                if duplicate:
                    raise ValidationError(
                        f"Lot {line.lot_id.name} already has a Customs ID."
                    )

                # ✅ Write to Purchase Order Line
                if line.purchase_line_id:
                    line.purchase_line_id.write({
                        'custom_id': line.custom_id
                    })

                # ✅ Write to Lot
                line.lot_id.write({
                    'custom_id': line.custom_id
                })

            record.status = 'confirmed'

    @api.model
    def create_lines(self):
        """Populate the operation with received car lots from related Done pickings.
        This method is idempotent: it will not create duplicate lines for lots that already have
        a custom_id or that are already present in this operation.
        """
        for record in self:
            order = record.purchase_order_id or record.sale_order_id
            if not order:
                continue

            # Map existing lot ids already present on this operation to avoid duplicate lines
            existing_lot_ids = record.line_ids.mapped('lot_id').ids

            # Get done pickings and map product -> list of lot records
            pickings = order.picking_ids.filtered(lambda p: p.state == 'done')
            lot_map = {}
            for ml in pickings.mapped('move_line_ids'):
                if ml.product_id.is_car and ml.lot_id:
                    lot_map.setdefault(ml.product_id.id, []).append(ml.lot_id)

            vals_list = []
            order_lines = order.order_line.filtered(lambda l: l.product_id.is_car)
            for line in order_lines:
                serials = lot_map.get(line.product_id.id, [])
                qty = int(line.product_uom_qty or 0)
                for i in range(qty):
                    lot = serials[i] if i < len(serials) else False

                    # Skip lots that already have customs assigned (they were processed earlier)
                    if lot and lot.custom_id:
                        continue

                    # Skip lots that already exist on this operation
                    if lot and lot.id in existing_lot_ids:
                        continue

                    # Build values; if lot is missing, allow creating an empty line (user will fill lot/custom)
                    vals = {
                        'head_id': record.id,
                        'product_id': line.product_id.id,
                        'lot_id': lot.id if lot else False,
                        'serial_chassis_number': lot.name if lot else False,
                        'quantity': 1,
                    }
                    vals_list.append(vals)

            if vals_list:
                self.env['stock.operation.customids.line'].create(vals_list)


class StockOperationLine(models.Model):
    _name = 'stock.operation.customids.line'
    _description = 'Inventory Operation CustomIDs Line'

    head_id = fields.Many2one('stock.operation.customids', string="Operation Reference", required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product", required=True)
    lot_id = fields.Many2one('stock.lot', string='Lot', domain="[('product_id','=', product_id)]")
    serial_chassis_number = fields.Char(string="Serial Number/Chassis Number")
    custom_id = fields.Char(string="Customs ID")
    quantity = fields.Integer(string="Quantity", default=1)
    purchase_line_id = fields.Many2one(
        'purchase.order.line',
        string="Purchase Order Line",
        ondelete='set null'
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'stock_operation_line_attachment_rel',
        'line_id',
        'attachment_id',
        string="Attachments"
    )

    @api.constrains('custom_id')
    def _check_unique_custom_id(self):
        for record in self:
            if not record.custom_id:
                continue

            # Check uniqueness against stock.lot
            domain = [('custom_id', '=', record.custom_id)]
            if record.lot_id:
                domain.append(('id', '!=', record.lot_id.id))

            existing_lot = self.env['stock.lot'].search(domain, limit=1)
            if existing_lot:
                raise ValidationError(
                    f"Customs ID '{record.custom_id}' is already assigned to Lot '{existing_lot.name}'."
                )

            # Ensure no duplicate custom_id in other operation lines
            dup = self.search([
                ('custom_id', '=', record.custom_id),
                ('id', '!=', record.id)
            ], limit=1)

            if dup:
                raise ValidationError(
                    f"Customs ID '{record.custom_id}' is already used in another operation."
                )

    @api.constrains('lot_id', 'head_id')
    def _check_duplicate_lot(self):
        for line in self:
            if not line.lot_id or not line.head_id.purchase_order_id:
                continue

            domain = [
                ('lot_id', '=', line.lot_id.id),
                ('head_id.purchase_order_id', '=', line.head_id.purchase_order_id.id),
                ('head_id.status', '=', 'confirmed'),
                ('id', '!=', line.id),
            ]

            if self.search_count(domain):
                raise ValidationError(
                    f"Lot '{line.lot_id.name}' already has a confirmed Customs ID for this Purchase Order."
                )


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def unlink(self):
        """ Prevent document deletion when status is not 'draft' for stock.operation.customids only """
        for attachment in self:
            if attachment.res_model == 'stock.operation.customids':
                related_record = self.env[attachment.res_model].browse(attachment.res_id)
                if related_record and related_record.exists() and related_record.status != 'draft':
                    raise UserError("You cannot delete attachments when the status is not 'draft'.")
        return super(IrAttachment, self).unlink()
