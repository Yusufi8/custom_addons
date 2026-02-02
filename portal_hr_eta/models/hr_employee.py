from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_ids = fields.One2many(
        'hr.employee',
        compute='_compute_employee_ids',
        string='Employees'
    )

    def _compute_employee_ids(self):
        for record in self:
            record.employee_ids = False
