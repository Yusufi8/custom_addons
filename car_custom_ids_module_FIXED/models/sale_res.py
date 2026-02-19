from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleResOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Sale Order Extension for Hospital Appointments'

    appointment_id = fields.Many2one(
        'hospital.appointment', string='Appointment'
    )

