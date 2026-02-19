from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_car = fields.Boolean(string="Is Car")

    @api.onchange("is_car")
    def _onchange_is_car(self):
        for rec in self:
            if rec.is_car:
                rec.type = 'consu'
                rec.tracking = 'serial'

    @api.constrains("is_car", "type", "tracking")
    def _check_car_rules(self):
        for rec in self:
            if rec.is_car:
                if rec.type != "consu":
                    raise ValidationError(
                        "Car products must be of type 'Goods'."
                    )
                if rec.tracking != "serial":
                    raise ValidationError(
                        "Car products must use Serial tracking."
                    )
# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
# from odoo.exceptions import ValidationError, UserError,AccessError
#
#
# class ProductTemplate(models.Model):
#     _inherit = "product.template"
#
#     is_car = fields.Boolean(string="Is Car")
#
#     @api.constrains("is_car", "type", "tracking")
#     def _check_car_rules(self):
#         for rec in self:
#             if rec.is_car:
#                 # Expect product type 'consu' (Goods) in this module's configuration
#                 if rec.type != "consu":
#                     raise ValidationError("Car products must be of type 'Goods'.")
#                 if rec.tracking != "serial":
#                     raise ValidationError("Car products must use Serial tracking.")
#     @api.onchange("is_car")
#     def _onchange_is_car(self):
#         for rec in self:
#             if rec.is_car:
#                 rec.type = 'consu'
#                 rec.tracking = 'serial'
#             return {}
#
#     @api.model
#     def _get_default_product_type(self):
#         return 'consu'
#
#     @api.model
#     def _get_default_tracking(self):
#         return 'serial'
#
#     @api.model
#     def default_get(self, fields):
#         res = super().default_get(fields)
#         if 'is_car' in fields and res.get('is_car'):
#             res['type'] = self._get_default_product_type()
#             res['tracking'] = self._get_default_tracking()
#         return res
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         for vals in vals_list:
#             if vals.get('is_car'):
#                 vals.setdefault('type', 'consu')
#                 vals.setdefault('tracking', 'serial')
#         return super().create(vals_list)
