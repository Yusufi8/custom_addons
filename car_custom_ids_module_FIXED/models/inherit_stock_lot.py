from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockLot(models.Model):
    _inherit = "stock.lot"

    custom_id = fields.Char("Customs ID", copy=False, index=True)

    # ------------------------------------------------------------------
    # Original flags – kept for any existing code that depends on them
    # ------------------------------------------------------------------
    is_sold = fields.Boolean(compute="_compute_sale_status", store=False)
    is_qualified = fields.Boolean(compute="_compute_sale_status", store=False)

    # ------------------------------------------------------------------
    # FIELD 1 – lot_status  (Char, displayed as coloured badge text)
    #
    #   🟥  SOLD      → confirmed / done sale order exists
    #   🟩  READY     → has Customs ID, no active SO
    #   🟧  PENDING   → draft / sent SO exists (not yet confirmed)
    #   🟦  NEW       → no Customs ID, never sold
    # ------------------------------------------------------------------
    lot_status = fields.Char(
        string="Status",
        compute="_compute_lot_status_fields",
        store=False,
        help=(
            "SOLD    – used in a confirmed/done sale order\n"
            "READY   – has Customs ID, available for sale\n"
            "PENDING – linked to a draft/sent sale order\n"
            "NEW     – no Customs ID, never sold"
        ),
    )

    # ------------------------------------------------------------------
    # FIELD 2 – sale_order_ref  (Char)
    # "S00209 [Done]"  or  "S00211 [Confirmed],  S00215 [Draft]"
    # ------------------------------------------------------------------
    sale_order_ref = fields.Char(
        string="Sale Order Ref",
        compute="_compute_lot_status_fields",
        store=False,
        help="Sale Order(s) linked to this lot with their current state.",
    )

    _sql_constraints = [
        (
            "custom_id_uniq",
            "unique(custom_id, company_id)",
            "Customs ID must be unique per company!",
        ),
    ]

    # ------------------------------------------------------------------
    # Prevent lot name == custom_id
    # ------------------------------------------------------------------
    def write(self, vals):
        if "custom_id" in vals:
            for lot in self:
                if lot.name and lot.name.strip() == vals.get("custom_id", "").strip():
                    raise ValidationError(
                        "Lot / Serial Number and Customs ID cannot be the same."
                    )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Original compute (kept for is_sold / is_qualified)
    # ------------------------------------------------------------------
    def _compute_sale_status(self):
        for lot in self:
            sold = self.env["sale.order.line"].search_count([
                ("lot_ids", "=", lot.id),
                ("order_id.state", "not in", ["cancel", "draft", "sent"]),
            ])
            lot.is_sold = bool(sold)
            lot.is_qualified = bool(lot.custom_id) and not lot.is_sold

    # ------------------------------------------------------------------
    # State label map
    # ------------------------------------------------------------------
    _SO_STATE_LABEL = {
        "draft":  "Draft",
        "sent":   "Sent",
        "sale":   "Confirmed",
        "done":   "Done",
        "cancel": "Cancelled",
    }

    # ------------------------------------------------------------------
    # Main compute – single DB pass for both new fields
    # ------------------------------------------------------------------
    def _compute_lot_status_fields(self):
        for lot in self:
            sol_records = self.env["sale.order.line"].search([
                ("lot_ids", "=", lot.id),
            ])

            active_orders = sol_records.filtered(
                lambda l: l.order_id.state in ("sale", "done")
            ).mapped("order_id")

            pending_orders = sol_records.filtered(
                lambda l: l.order_id.state in ("draft", "sent")
            ).mapped("order_id")

            # ── lot_status label (used by decoration-* and badge widget) ──
            if active_orders:
                lot.lot_status = "SOLD"
            elif pending_orders:
                lot.lot_status = "PENDING"
            elif lot.custom_id:
                lot.lot_status = "READY"
            else:
                lot.lot_status = "NEW"

            # ── sale_order_ref ──────────────────────────────────────────
            display_orders = (active_orders | pending_orders).sorted("name")
            if display_orders:
                parts = [
                    "{} [{}]".format(o.name, self._SO_STATE_LABEL.get(o.state, o.state))
                    for o in display_orders
                ]
                lot.sale_order_ref = ",  ".join(parts)
            else:
                lot.sale_order_ref = False

    # ------------------------------------------------------------------
    # Smart Dropdown Sorting in lot_ids popup:
    # READY → NEW → PENDING → SOLD
    # ------------------------------------------------------------------
    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        lots = self.search(args, limit=limit)
        _priority = {"READY": 0, "NEW": 1, "PENDING": 2, "SOLD": 3}
        lots = lots.sorted(key=lambda l: _priority.get(l.lot_status, 9))
        return lots.name_get()



# from odoo import models, fields, api
# from odoo.exceptions import ValidationError
#
#
# class StockLot(models.Model):
#     _inherit = "stock.lot"
#
#     custom_id = fields.Char("Customs ID", copy=False, index=True)
#
#     # -----------------------------
#     # Status Flags (original — kept for compatibility)
#     # -----------------------------
#     is_sold = fields.Boolean(
#         compute="_compute_sale_status",
#         store=False
#     )
#
#     is_qualified = fields.Boolean(
#         compute="_compute_sale_status",
#         store=False
#     )
#
#     # ----------------------------------------------------------------
#     # NEW FIELD 1: lot_status  (Char)
#     # Displays one of four states as a unicode symbol + label:
#     #
#     #   ● Sold      → linked to a confirmed / done sale order
#     #   ✔ Ready     → has custom_id, never sold / no active SO
#     #   ◑ Pending   → linked to a draft or sent (unconfirmed) SO
#     #   ◎ New       → no custom_id, no SO at all  (fresh/unused)
#     # ----------------------------------------------------------------
#     lot_status = fields.Char(
#         string="Status",
#         compute="_compute_lot_status_fields",
#         store=False,
#         help=(
#             "● Sold    – used in a confirmed/done sale order\n"
#             "✔ Ready   – has Customs ID, available for sale\n"
#             "◑ Pending – linked to a draft/sent sale order\n"
#             "◎ New     – no Customs ID, never sold"
#         ),
#     )
#
#     # ----------------------------------------------------------------
#     # NEW FIELD 2: sale_order_ref  (Char)
#     # Shows every linked SO with its current state, e.g.:
#     #   S00209 [Done],  S00211 [Confirmed]
#     # ----------------------------------------------------------------
#     sale_order_ref = fields.Char(
#         string="Sale Order Ref",
#         compute="_compute_lot_status_fields",
#         store=False,
#         help="Sale Order(s) linked to this lot together with their current state.",
#     )
#
#     # Keep is_ready so the boolean widget column still works
#     is_ready = fields.Boolean(
#         string="Ready",
#         compute="_compute_lot_status_fields",
#         store=False,
#     )
#
#     _sql_constraints = [
#         (
#             "custom_id_uniq",
#             "unique(custom_id, company_id)",
#             "Customs ID must be unique per company!",
#         ),
#     ]
#
#     # ------------------------------------------------------------------
#     # Prevent lot name == custom_id
#     # ------------------------------------------------------------------
#     def write(self, vals):
#         if "custom_id" in vals:
#             for lot in self:
#                 if lot.name and lot.name.strip() == vals.get("custom_id", "").strip():
#                     raise ValidationError(
#                         "Lot / Serial Number and Customs ID cannot be the same."
#                     )
#         return super().write(vals)
#
#     # ------------------------------------------------------------------
#     # Original compute (kept for is_sold / is_qualified)
#     # ------------------------------------------------------------------
#     def _compute_sale_status(self):
#         for lot in self:
#             sold = self.env["sale.order.line"].search_count([
#                 ("lot_ids", "=", lot.id),
#                 ("order_id.state", "not in", ["cancel", "draft", "sent"]),
#             ])
#             lot.is_sold = bool(sold)
#             lot.is_qualified = bool(lot.custom_id) and not lot.is_sold
#
#     # ------------------------------------------------------------------
#     # Human-readable state labels for sale.order.state
#     # ------------------------------------------------------------------
#     _SO_STATE_LABEL = {
#         "draft":  "Draft",
#         "sent":   "Sent",
#         "sale":   "Confirmed",
#         "done":   "Done",
#         "cancel": "Cancelled",
#     }
#
#     # ------------------------------------------------------------------
#     # Main compute for all new display fields (single DB pass)
#     # ------------------------------------------------------------------
#     def _compute_lot_status_fields(self):
#         for lot in self:
#             # All sale lines that reference this lot (any state)
#             sol_records = self.env["sale.order.line"].search([
#                 ("lot_ids", "=", lot.id),
#             ])
#
#             active_orders = sol_records.filtered(
#                 lambda l: l.order_id.state in ("sale", "done")
#             ).mapped("order_id")
#
#             pending_orders = sol_records.filtered(
#                 lambda l: l.order_id.state in ("draft", "sent")
#             ).mapped("order_id")
#
#             # ── is_ready: boolean tick / cross ──────────────────────
#             lot.is_ready = bool(lot.custom_id) and not bool(active_orders)
#
#             # ── lot_status: symbol + label ───────────────────────────
#             if active_orders:
#                 lot.lot_status = "● Sold"       # red filled circle  → used/sold
#             elif pending_orders:
#                 lot.lot_status = "◑ Pending"    # half-filled circle → in progress
#             elif lot.custom_id:
#                 lot.lot_status = "✔ Ready"      # tick               → ready to sell
#             else:
#                 lot.lot_status = "◎ New"        # open circle        → fresh / unused
#
#             # ── sale_order_ref: "S00209 [Done],  S00211 [Confirmed]" ─
#             display_orders = (active_orders | pending_orders).sorted("name")
#             if display_orders:
#                 parts = [
#                     "{} [{}]".format(
#                         o.name,
#                         self._SO_STATE_LABEL.get(o.state, o.state)
#                     )
#                     for o in display_orders
#                 ]
#                 lot.sale_order_ref = ",  ".join(parts)
#             else:
#                 lot.sale_order_ref = False
#
#     # ------------------------------------------------------------------
#     # Smart Dropdown Sorting
#     # Priority: Ready → New → Pending → Sold
#     # ------------------------------------------------------------------
#     @api.model
#     def name_search(self, name="", args=None, operator="ilike", limit=100):
#         args = args or []
#         lots = self.search(args, limit=limit)
#
#         _priority = {
#             "✔ Ready":   0,
#             "◎ New":     1,
#             "◑ Pending": 2,
#             "● Sold":    3,
#         }
#         lots = lots.sorted(key=lambda l: _priority.get(l.lot_status, 9))
#
#         return lots.name_get()
#








# from odoo import models, fields, api
# from odoo.exceptions import ValidationError
#
#
# class StockLot(models.Model):
#     _inherit = "stock.lot"
#
#     custom_id = fields.Char("Customs ID", copy=False, index=True)
#
#     # -----------------------------
#     # Status Flags
#     # -----------------------------
#     is_sold = fields.Boolean(
#         compute="_compute_sale_status",
#         store=False
#     )
#
#     is_qualified = fields.Boolean(
#         compute="_compute_sale_status",
#         store=False
#     )
#
#     # -----------------------------
#     # NEW FIELD 1: Ready-to-use status icon
#     # True  → ✔ (ready: has custom_id, not sold)
#     # False → ✘ (sold or not qualified)
#     # -----------------------------
#     is_ready = fields.Boolean(
#         string="Ready",
#         compute="_compute_lot_status_fields",
#         store=False,
#         help="Checked (✔) when the lot has a Customs ID and has not been sold yet. "
#              "Unchecked (✘) when it is already sold or not qualified."
#     )
#
#     # -----------------------------
#     # NEW FIELD 2: Related Sale Order reference
#     # Shows the sale order name(s) linked to this lot
#     # -----------------------------
#     sale_order_ref = fields.Char(
#         string="Sale Order Ref",
#         compute="_compute_lot_status_fields",
#         store=False,
#         help="Reference of the Sale Order(s) that contain this lot."
#     )
#
#     _sql_constraints = [
#         (
#             "custom_id_uniq",
#             "unique(custom_id, company_id)",
#             "Customs ID must be unique per company!"
#         ),
#     ]
#
#     # -----------------------------
#     # Prevent same value for lot name & custom_id
#     # -----------------------------
#     def write(self, vals):
#         if 'custom_id' in vals:
#             for lot in self:
#                 if lot.name and lot.name.strip() == vals.get('custom_id', '').strip():
#                     raise ValidationError(
#                         "Lot / Serial Number and Customs ID cannot be the same."
#                     )
#         return super().write(vals)
#
#     # -----------------------------
#     # Compute Sale Status (original)
#     # -----------------------------
#     def _compute_sale_status(self):
#         for lot in self:
#             sold = self.env["sale.order.line"].search_count([
#                 ("lot_ids", "=", lot.id),
#                 ("order_id.state", "!=", "cancel"),
#             ])
#
#             lot.is_sold = bool(sold)
#             lot.is_qualified = bool(lot.custom_id) and not lot.is_sold
#
#     # -----------------------------
#     # Compute NEW fields:
#     #   is_ready       → True if has custom_id AND not sold
#     #   sale_order_ref → comma-separated sale order names linked to this lot
#     # -----------------------------
#     def _compute_lot_status_fields(self):
#         for lot in self:
#             # --- Fetch all non-cancelled sale order lines that contain this lot ---
#             sol_records = self.env["sale.order.line"].search([
#                 ("lot_ids", "=", lot.id),
#                 ("order_id.state", "!=", "cancel"),
#             ])
#
#             sold = bool(sol_records)
#
#             # is_ready: tick ✔ means ready to use (has Customs ID, not sold)
#             #           cross ✘ means already sold OR not qualified
#             lot.is_ready = bool(lot.custom_id) and not sold
#
#             # sale_order_ref: collect unique SO names, e.g. "S00001, S00002"
#             if sol_records:
#                 order_names = sol_records.mapped("order_id.name")
#                 lot.sale_order_ref = ", ".join(sorted(set(order_names)))
#             else:
#                 lot.sale_order_ref = False
#
#     # -----------------------------
#     # Smart Dropdown Sorting
#     # -----------------------------
#     @api.model
#     def name_search(self, name='', args=None, operator='ilike', limit=100):
#         args = args or []
#         lots = self.search(args, limit=limit)
#
#         # Sorting logic:
#         # 1️⃣ Qualified first
#         # 2️⃣ Not sold next
#         # 3️⃣ Sold last
#         lots = lots.sorted(
#             key=lambda l: (
#                 not l.is_qualified,
#                 l.is_sold
#             )
#         )
#
#         return lots.name_get()
#
#
#
#
#
#



