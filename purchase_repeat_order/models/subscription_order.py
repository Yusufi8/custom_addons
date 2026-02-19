# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionPurchaseOrder(models.Model):
    _name = 'subscription.purchase.order'
    _description = 'Subscription Purchase Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    # =========================================================
    # BASIC INFORMATION
    # =========================================================

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        default="New",
        tracking=True
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string="Vendor",
        required=True,
        tracking=True
    )

    product_id = fields.Many2one(
        'product.product',
        string="Product",
        required=True,
        tracking=True
    )

    product_description = fields.Text(string="Description")

    po_type = fields.Selection([
        ('regular', 'Regular'),
        ('contract', 'Contract')
    ], string="PO Type", default='regular')

    days_to_notify = fields.Integer(string="Days to Notify", default=1)

    quantity = fields.Float(default=1.0, required=True)
    unit_price = fields.Float(string="Unit Price", required=True, default=1.0)
    unit = fields.Many2one('uom.uom', string="Unit of Measure")

    # =========================================================
    # SUBSCRIPTION LOGIC
    # =========================================================

    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
    ], required=True)

    start_date = fields.Datetime(
        required=True,
        default=fields.Datetime.now
    )

    last_invoice_date = fields.Datetime(
        string="Last PO Date",
        default=fields.Datetime.now,
        tracking=True
    )

    next_invoice_date = fields.Datetime(
        string="Next PO Date",
        compute="_compute_next_invoice_date",
        store=True,
        tracking=True
    )

    # =========================================================
    # AMOUNTS
    # =========================================================

    sub_amount = fields.Float(string="Subtotal", compute="_compute_amount", store=True)
    tax = fields.Many2one('account.tax', string="Tax")
    amount = fields.Float(string="Total Amount", compute="_compute_amount", store=True)

    payment_method = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic')
    ], string="Payment Method")

    payment_type = fields.Selection([
        ('credit', 'Credit Card'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash')
    ], string="Payment Type")

    # =========================================================
    # PURCHASE ORDER LINK
    # =========================================================

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string="Last PO",
        tracking=True
    )

    po_count = fields.Integer(string="PO Count", compute="_compute_po_count")

    # =========================================================
    # STATE
    # =========================================================

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('closed', 'Closed'),
    ], default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True
    )

    # =========================================================
    # SEQUENCE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'subscription.purchase.order'
                ) or 'New'
        return super().create(vals_list)

    # =========================================================
    # COMPUTE METHODS
    # =========================================================

    @api.depends('quantity', 'unit_price', 'tax')
    def _compute_amount(self):
        for rec in self:
            subtotal = rec.quantity * rec.unit_price
            rec.sub_amount = subtotal
            if rec.tax:
                taxes = rec.tax.compute_all(rec.unit_price, quantity=rec.quantity)
                rec.amount = taxes['total_included']
            else:
                rec.amount = subtotal

    @api.depends('last_invoice_date', 'frequency')
    def _compute_next_invoice_date(self):
        for rec in self:
            if not rec.last_invoice_date or not rec.frequency:
                rec.next_invoice_date = False
                continue

            if rec.frequency == 'daily':
                rec.next_invoice_date = rec.last_invoice_date + timedelta(days=1)
            elif rec.frequency == 'weekly':
                rec.next_invoice_date = rec.last_invoice_date + timedelta(days=7)
            elif rec.frequency == 'monthly':
                rec.next_invoice_date = rec.last_invoice_date + relativedelta(months=1)
            elif rec.frequency == 'quarterly':
                rec.next_invoice_date = rec.last_invoice_date + relativedelta(months=3)
            elif rec.frequency == 'half_yearly':
                rec.next_invoice_date = rec.last_invoice_date + relativedelta(months=6)
            elif rec.frequency == 'yearly':
                rec.next_invoice_date = rec.last_invoice_date + relativedelta(years=1)

    def _compute_po_count(self):
        for rec in self:
            rec.po_count = self.env['purchase.order'].search_count([
                ('origin', '=', rec.name)
            ])

    # =========================================================
    # VALIDATIONS
    # =========================================================

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("Quantity must be greater than 0."))

    @api.constrains('unit_price')
    def _check_unit_price(self):
        for rec in self:
            if rec.unit_price <= 0:
                raise ValidationError(_("Unit price must be greater than 0."))

    # =========================================================
    # CRON AUTOMATION
    # =========================================================

    @api.model
    def _cron_process_subscriptions(self):
        now = fields.Datetime.now()

        subscriptions = self.sudo().search([
            ('state', '=', 'running'),
            ('next_invoice_date', '<=', now)
        ])

        _logger.warning(f"Found {len(subscriptions)} subscriptions to process")

        for subscription in subscriptions:
            try:
                po = subscription._create_subscription_po()

                if subscription.payment_method == 'automatic':
                    po.button_confirm()

                subscription._send_subscription_email()

            except Exception as e:
                _logger.error(f"Error processing {subscription.name}: {e}")

    # =========================================================
    # INTERNAL HELPERS
    # =========================================================

    def _create_subscription_po(self):
        self.ensure_one()

        po_vals = {
            'partner_id': self.vendor_id.id,
            'origin': self.name,
            'order_line': [(0, 0, {
                'product_id': self.product_id.id,
                'product_qty': self.quantity,
                'price_unit': self.unit_price,
                'product_uom': (self.unit or self.product_id.uom_id).id,
                'taxes_id': [(6, 0, [self.tax.id])] if self.tax else [],
                'date_planned': fields.Date.today(),
                'name': self.product_description or self.product_id.display_name,
            })]
        }

        po = self.env['purchase.order'].create(po_vals)

        self.write({
            'last_invoice_date': fields.Datetime.now(),
            'purchase_order_id': po.id
        })

        return po

    def _send_subscription_email(self):
        self.ensure_one()

        if not self.vendor_id or not self.vendor_id.email:
            _logger.warning(f"No email found for vendor {self.vendor_id.name}")
            return

        template = self.env.ref(
            'purchase_repeat_order.email_template_subscription_po',
            raise_if_not_found=False
        )

        if template:
            template.send_mail(
                self.id,
                force_send=True,
                email_values={
                    'email_to': self.vendor_id.email
                }
            )

    # =========================================================
    # BUTTON ACTIONS
    # =========================================================

    def action_start(self):
        self.write({'state': 'running'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_raise_po(self):
        self.ensure_one()

        if self.state != 'running':
            raise UserError(_("Subscription must be running to raise a Purchase Order."))

        po = self._create_subscription_po()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Order'),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': po.id,
            'target': 'current',
        }

    def action_view_po(self):
        self.ensure_one()
        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('origin', '=', self.name)],
            'context': {'create': False},
        }












# # -*- coding: utf-8 -*-
# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError, UserError, AccessError
# from datetime import timedelta
# from dateutil.relativedelta import relativedelta
# import logging
# _logger = logging.getLogger(__name__)
#
# class SubscriptionPurchaseOrder(models.Model):
#     _name = 'subscription.purchase.order'
#     _description = 'Subscription Purchase Order'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _rec_name = 'name'
#     _order = 'id desc'
#
#     # =========================================================
#     # BASIC INFORMATION
#     # =========================================================
#
#     name = fields.Char(
#         string="Reference",
#         required=True,
#         copy=False,
#         default="New",
#         tracking=True
#     )
#
#     vendor_id = fields.Many2one(
#         'res.partner',
#         string="Vendor",
#         required=True,
#         tracking=True
#     )
#
#     product_id = fields.Many2one(
#         'product.product',
#         string="Product",
#         required=True,
#         tracking=True
#     )
#
#     product_description = fields.Text(string="Description")
#
#     po_type = fields.Selection([
#         ('regular', 'Regular'),
#         ('contract', 'Contract')
#     ], string="PO Type", default='regular')
#
#     days_to_notify = fields.Integer(
#         string="Days to Notify",
#         default=1
#     )
#
#     quantity = fields.Float(default=1.0, required=True)
#     unit_price = fields.Float(
#         string="Unit Price",
#         required=True,
#         tracking=True,
#         default=1.0
#     )
#
#     unit = fields.Many2one('uom.uom', string="Unit of Measure")
#
#     # =========================================================
#     # SUBSCRIPTION LOGIC
#     # =========================================================
#
#     frequency = fields.Selection([
#         ('daily', 'Daily'),
#         ('weekly', 'Weekly'),
#         ('monthly', 'Monthly'),
#         ('quarterly', 'Quarterly'),
#         ('half_yearly', 'Half Yearly'),
#         ('yearly', 'Yearly'),
#     ], required=True, tracking=True)
#
#     start_date = fields.Datetime(
#         required=True,
#
#     )
#
#     last_invoice_date = fields.Datetime(
#         string="Last PO Date",
#         default=fields.Date.today,
#         tracking=True
#     )
#
#     next_invoice_date = fields.Datetime(
#         string="Next PO Date",
#         compute="_compute_next_invoice_date",
#         store=True,
#         tracking=True
#     )
#
#     # =========================================================
#     # AMOUNTS
#     # =========================================================
#
#     sub_amount = fields.Float(
#         string="Subtotal",
#         compute="_compute_amount",
#         store=True
#     )
#
#     tax = fields.Many2one('account.tax', string="Tax")
#
#     amount = fields.Float(
#         string="Total Amount",
#         compute="_compute_amount",
#         store=True
#     )
#
#     payment_method = fields.Selection([
#         ('manual', 'Manual'),
#         ('automatic', 'Automatic')
#     ], string="Payment Method")
#
#     payment_type = fields.Selection([
#         ('credit', 'Credit Card'),
#         ('bank', 'Bank Transfer'),
#         ('cash', 'Cash')
#     ], string="Payment Type")
#
#     # =========================================================
#     # PURCHASE ORDER LINK
#     # =========================================================
#
#     purchase_order_id = fields.Many2one(
#         'purchase.order',
#         string="Last PO",
#         tracking=True
#     )
#
#     po_count = fields.Integer(
#         string="PO Count",
#         compute="_compute_po_count"
#     )
#
#     # =========================================================
#     # STATE
#     # =========================================================
#
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('running', 'Running'),
#         ('closed', 'Closed'),
#     ], default='draft', tracking=True)
#
#     # =========================================================
#     # SEQUENCE
#     # =========================================================
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         for vals in vals_list:
#             if vals.get('name', 'New') == 'New':
#                 vals['name'] = self.env['ir.sequence'].next_by_code(
#                     'subscription.purchase.order'
#                 ) or 'New'
#         return super().create(vals_list)
#
#     # =========================================================
#     # COMPUTE METHODS
#     # =========================================================
#
#     @api.depends('quantity', 'unit_price', 'tax')
#     def _compute_amount(self):
#         for rec in self:
#             subtotal = rec.quantity * rec.unit_price
#             rec.sub_amount = subtotal
#
#             if rec.tax:
#                 taxes = rec.tax.compute_all(
#                     rec.unit_price,
#                     quantity=rec.quantity
#                 )
#                 rec.amount = taxes['total_included']
#             else:
#                 rec.amount = subtotal
#
#     @api.depends('last_invoice_date', 'frequency')
#     def _compute_next_invoice_date(self):
#         for rec in self:
#             if not rec.last_invoice_date or not rec.frequency:
#                 rec.next_invoice_date = False
#                 continue
#
#             if rec.frequency == 'daily':
#                 rec.next_invoice_date = rec.last_invoice_date + timedelta(days=1)
#             elif rec.frequency == 'weekly':
#                 rec.next_invoice_date = rec.last_invoice_date + timedelta(days=7)
#             elif rec.frequency == 'monthly':
#                 rec.next_invoice_date = rec.last_invoice_date + relativedelta(months=1)
#             elif rec.frequency == 'quarterly':
#                 rec.next_invoice_date = rec.last_invoice_date + relativedelta(months=3)
#             elif rec.frequency == 'half_yearly':
#                 rec.next_invoice_date = rec.last_invoice_date + relativedelta(months=6)
#             elif rec.frequency == 'yearly':
#                 rec.next_invoice_date = rec.last_invoice_date + relativedelta(years=1)
#
#     def _compute_po_count(self):
#         for rec in self:
#             rec.po_count = self.env['purchase.order'].search_count([
#                 ('origin', '=', rec.name)
#             ])
#
#     # =========================================================
#     # VALIDATIONS
#     # =========================================================
#
#     @api.constrains('quantity')
#     def _check_quantity(self):
#         for rec in self:
#             if rec.quantity <= 0:
#                 raise ValidationError(_("Quantity must be greater than 0."))
#
#     @api.constrains('unit_price')
#     def _check_unit_price(self):
#         for rec in self:
#             if rec.unit_price <= 0:
#                 raise ValidationError(_("Unit price must be greater than 0."))
#
#     # =========================================================
#     # CRON AUTOMATION
#     # =========================================================
#     @api.model
#     def _cron_process_subscriptions(self):
#         today = fields.Datetime.now()
#
#
#         subscriptions = self.sudo().search([
#             ('state', '=', 'running'),
#             ('next_invoice_date', '=', today)
#         ])
#
#         for subscription in subscriptions:
#             try:
#                 _logger.info(f"Processing subscription {subscription.name}")
#
#                 po = subscription.sudo()._create_subscription_po()
#
#                 if subscription.payment_method == 'automatic':
#                     po.sudo().button_confirm()
#
#                 subscription.sudo()._send_subscription_email(po)
#
#             except Exception as e:
#                 _logger.error(f"Error processing subscription {subscription.name}: {e}")
#
#     # @api.model
#     # def _cron_process_subscriptions(self):
#     #     today = fields.Date.today()
#     #
#     #     subscriptions = self.search([
#     #         ('state', '=', 'running'),
#     #         ('next_invoice_date', '<=', today)
#     #     ])
#     #
#     #     for subscription in subscriptions:
#     #
#     #         # Prevent duplicate execution
#     #         if subscription.last_invoice_date == today:
#     #             continue
#     #
#     #         # Reminder logic
#     #         if subscription.days_to_notify:
#     #             reminder_date = subscription.next_invoice_date - timedelta(days=subscription.days_to_notify)
#     #             if reminder_date == today:
#     #                 subscription._send_subscription_reminder()
#     #                 continue
#     #
#     #         # Create PO
#     #         po = subscription._create_subscription_po()
#     #
#     #         # Automatic payment logic
#     #         if subscription.payment_method == 'automatic':
#     #             po.button_confirm()
#     #
#     #         # Send email notification
#     #         subscription._send_subscription_email(po)
#
#     # =========================================================
#     # INTERNAL HELPERS
#     # =========================================================
#
#     def _create_subscription_po(self):
#         self.ensure_one()
#
#         po_vals = {
#             'partner_id': self.vendor_id.id,
#             'origin': self.name,
#             'order_line': [(0, 0, {
#                 'product_id': self.product_id.id,
#                 'product_qty': self.quantity,
#                 'price_unit': self.unit_price,
#                 'product_uom': (self.unit or self.product_id.uom_id).id,
#                 'taxes_id': [(6, 0, [self.tax.id])] if self.tax else [],
#                 'date_planned': fields.Date.today(),
#                 'name': self.product_description or self.product_id.display_name,
#             })]
#         }
#
#         po = self.env['purchase.order'].create(po_vals)
#
#         self.last_invoice_date = fields.Date.today()
#         self.purchase_order_id = po.id
#         self._compute_next_invoice_date()
#
#         return po
#
#     def _send_subscription_email(self, po):
#         if not self.vendor_id.email:
#             return
#
#         template = self.env.ref(
#             'purchase_repeat_order.email_template_subscription_po',
#             raise_if_not_found=False
#         )
#
#         if template:
#             template.send_mail(self.id, force_send=True)
#
#     def _send_subscription_reminder(self):
#         if not self.vendor_id.email:
#             return
#
#         template = self.env.ref(
#             'purchase_repeat_order.email_template_subscription_reminder',
#             raise_if_not_found=False
#         )
#
#         if template:
#             template.send_mail(self.id, force_send=True)
#
#     # =========================================================
#     # BUTTON ACTIONS
#     # =========================================================
#
#     def action_start(self):
#         self.write({'state': 'running'})
#
#     def action_close(self):
#         self.write({'state': 'closed'})
#
#     def action_raise_po(self):
#         self.ensure_one()
#
#         if self.state != 'running':
#             raise UserError(_("Subscription must be running to raise a Purchase Order."))
#
#         po = self._create_subscription_po()
#
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Purchase Order'),
#             'res_model': 'purchase.order',
#             'view_mode': 'form',
#             'res_id': po.id,
#             'target': 'current',
#         }
#
#     def action_view_po(self):
#         self.ensure_one()
#         return {
#             'name': _('Purchase Orders'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.order',
#             'view_mode': 'list,form',
#             'domain': [('origin', '=', self.name)],
#             'context': {'create': False},
#         }
#
#
#
#
#
#
#
