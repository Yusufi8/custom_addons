from odoo import models, fields, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Lock flag after Close
    is_closed_operation = fields.Boolean(default=False)

    # -------------------------
    # RO BUTTON
    # -------------------------
    def action_repeat_order(self):
        self.ensure_one()

        if self.is_closed_operation:
            raise ValidationError(_("This Purchase Order is closed."))

        if not self.order_line:
            raise ValidationError(_("Cannot repeat a Purchase Order without lines."))

        # 🔑 Get BASE PO name (before -RO)
        base_name = self.name.split('-RO')[0]

        # Count existing ROs from base
        ro_count = self.search_count([
            ('name', 'like', f"{base_name}-RO%")
        ])

        new_name = f"{base_name}-RO{ro_count + 1}"

        new_order = self.copy({
            'name': new_name,
            'state': 'draft',
            'is_closed_operation': False,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Repeated Purchase Order'),
            'res_model': 'purchase.order',
            'res_id': new_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # -------------------------
    # CLOSE BUTTON
    # -------------------------
    def action_close_operation(self):
        self.ensure_one()

        # Confirm if needed
        if self.state == 'draft':
            self.button_confirm()

        # Mark completed & lock
        self.write({
            'state': 'done',
            'is_closed_operation': True,
        })

        return {'type': 'ir.actions.act_window_close'}

