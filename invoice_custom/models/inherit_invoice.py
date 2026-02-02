from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError, AccessError

class AccountMove(models.Model):
    _inherit = 'account.move'

    confirmed_by = fields.Date(
        string="Confirmed Date",
        tracking=True,
        required=True,
        help="Date when the invoice was confirmed",
    )

    # is_confirmed = fields.Boolean(
    #     string="Is Confirmed",
    #     default=False,
    #     copy=False
    # )


    # def action_post(self):
    #     res = super().action_post()
    #     for move in self:
    #         if not move.is_confirmed:
    #             move.confirmed_by = fields.Date.context_today(self)
    #             move.is_confirmed = True
    #     return res
