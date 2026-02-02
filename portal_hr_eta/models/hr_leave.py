from odoo import models

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    # ❌ CUSTOM ATTACHMENT FIELD (DISABLED)
    # This is replaced by Odoo native "Supporting Documents"
    #
    # attachment_ids = fields.Many2many(
    #     'ir.attachment',
    #     'hr_leave_ir_attachment_rel',
    #     'leave_id',
    #     'attachment_id',
    #     string='Attachments'
    # )

    # ✅ Odoo native field (DO NOT redefine)
    # supported_attachment_ids
    # pass
