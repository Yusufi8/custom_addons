from odoo import api, fields, models


class SaleOrderLinePopup(models.TransientModel):
    _name = 'sale.order.line.popup'
    _description = 'Popup to add sale order line (with lots)'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_image = fields.Binary(related='product_id.image_1920', readonly=True)
    product_description = fields.Html(related='product_id.description_sale', readonly=True)
    product_uom_qty = fields.Float('Quantity', default=1.0, required=True)
    product_uom = fields.Many2one('uom.uom', string='UoM')
    price_unit = fields.Float('Unit Price')
    total = fields.Monetary(string='Total', compute='_compute_total', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', readonly=True)
    tax_id = fields.Many2many('account.tax', string='Taxes')
    name = fields.Char('Description')
    lot_ids = fields.Many2many('stock.lot', string='Serial Numbers', domain="[('product_id','=', product_id)]")
    order_id = fields.Many2one('sale.order', string='Order')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.product_uom = rec.product_id.uom_id.id
                rec.price_unit = rec.product_id.lst_price
                rec.name = rec.product_id.display_name

    @api.depends('price_unit', 'product_uom_qty')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.price_unit * rec.product_uom_qty

    def action_confirm_add(self):
        """Create the sale.order.line with selected values on the parent sale order."""
        self.ensure_one()
        order = self.order_id
        if not order:
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        line_vals = {
            'order_id': order.id,
            'product_id': self.product_id.id,
            'product_uom_qty': self.product_uom_qty,
            'product_uom': self.product_uom.id if self.product_uom else False,
            'price_unit': self.price_unit,
            'tax_id': [(6, 0, self.tax_id.ids)] if self.tax_id else False,
            'name': self.name,
        }
        # Include lot_ids in create values to avoid constraint errors during create
        if self.lot_ids:
            line_vals['lot_ids'] = [(6, 0, self.lot_ids.ids)]

        created_lines = self.env['sale.order.line'].create([line_vals])
        line = created_lines[0]
        return {'type': 'ir.actions.act_window_close'}

