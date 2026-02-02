# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SaleOrderRestAPI(http.Controller):

    # ---------------------------------------------------
    # Helper → Get Sale Order by ID or NAME
    # ---------------------------------------------------
    def _get_so(self, identifier):
        SaleOrder = request.env['sale.order'].sudo()

        # Try numeric ID
        if str(identifier).isdigit():
            so = SaleOrder.browse(int(identifier))
            if so.exists():
                return so

        # Fallback to SO number (name)
        return SaleOrder.search([('name', '=', identifier)], limit=1)

    # ===================================================
    # GET → All Sale Orders
    # ===================================================
    @http.route('/api/v2/sales', type='http', auth='user',
                methods=['GET'], csrf=False)
    def get_sales(self, **kwargs):
        sales = request.env['sale.order'].sudo().search([])

        data = [{
            'id': so.id,
            'name': so.name,
            'customer': so.partner_id.name if so.partner_id else None,
            'state': so.state,
            'date_order': so.date_order,
            'amount_total': so.amount_total,
            'currency': so.currency_id.name if so.currency_id else None,
        } for so in sales]

        return request.make_json_response({
            'status': 'success',
            'count': len(data),
            'data': data
        })

    # ===================================================
    # GET → Single Sale Order (ID or NAME)
    # ===================================================
    @http.route('/api/v2/sales/<string:identifier>', type='http',
                auth='user', methods=['GET'], csrf=False)
    def get_sale(self, identifier, **kwargs):
        so = self._get_so(identifier)

        if not so:
            return request.make_json_response(
                {'status': 'error', 'message': 'Sale Order not found'},
                status=404
            )

        data = {
            'id': so.id,
            'name': so.name,
            'customer': so.partner_id.name if so.partner_id else None,
            'state': so.state,
            'date_order': so.date_order,
            'amount_total': so.amount_total,
            'lines': [{
                'line_id': l.id,
                'product_id': l.product_id.id,
                'product': l.product_id.name,
                'quantity': l.product_uom_qty,
                'price_unit': l.price_unit,
                'subtotal': l.price_subtotal,
            } for l in so.order_line]
        }

        return request.make_json_response({'status': 'success', 'data': data})

    # ===================================================
    # POST → Create Sale Order
    # ===================================================
    @http.route('/api/v2/sales', type='http', auth='user',
                methods=['POST'], csrf=False)
    def create_sale(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.data or '{}')

            if not payload.get('partner_id') or not payload.get('order_lines'):
                return request.make_json_response(
                    {'status': 'error', 'message': 'partner_id and order_lines required'},
                    status=400
                )

            partner = request.env['res.partner'].sudo().browse(payload['partner_id'])
            if not partner.exists():
                return request.make_json_response(
                    {'status': 'error', 'message': 'Invalid partner_id'},
                    status=400
                )

            # 🔑 Pricelist (MANDATORY)
            pricelist = partner.property_product_pricelist
            if not pricelist:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Customer has no pricelist'},
                    status=400
                )

            lines = []
            for line in payload['order_lines']:
                product = request.env['product.product'].sudo().browse(line['product_id'])
                if not product.exists():
                    return request.make_json_response(
                        {'status': 'error', 'message': f"Invalid product_id {line['product_id']}"},
                        status=400
                    )

                lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': line.get('quantity', 1),
                    'price_unit': line.get('price_unit', product.lst_price),
                }))

            so = request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'pricelist_id': pricelist.id,  # ✅ REQUIRED
                'order_line': lines,
            })

            return request.make_json_response(
                {'status': 'success', 'id': so.id, 'name': so.name},
                status=201
            )

        except Exception as e:
            _logger.exception("Error creating sale order")
            return request.make_json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )

    # ===================================================
    # PUT → Full Update Sale Order (LINES)
    # ===================================================
    @http.route('/api/v2/sales/<string:identifier>', type='http',
                auth='user', methods=['PUT'], csrf=False)
    def put_sale(self, identifier, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        so = self._get_so(identifier)

        if not so:
            return request.make_json_response(
                {'status': 'error', 'message': 'Sale Order not found'},
                status=404
            )

        commands = []

        # Update existing lines
        for line in payload.get('update_lines', []):
            commands.append((1, line['line_id'], {
                'product_uom_qty': line.get('quantity'),
                'price_unit': line.get('price_unit'),
            }))

        # Add new lines
        for line in payload.get('new_lines', []):
            commands.append((0, 0, {
                'product_id': line['product_id'],
                'product_uom_qty': line.get('quantity', 1),
                'price_unit': line.get('price_unit', 0),
            }))

        # Delete lines
        for line_id in payload.get('delete_lines', []):
            commands.append((2, line_id, 0))

        if commands:
            so.write({'order_line': commands})

        return request.make_json_response(
            {'status': 'success', 'message': 'Sale Order updated'}
        )

    # ===================================================
    # PATCH → Partial Update Sale Order (HEADER ONLY)
    # ===================================================
    @http.route('/api/v2/sales/<string:identifier>', type='http',
                auth='user', methods=['PATCH'], csrf=False)
    def patch_sale(self, identifier, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        so = self._get_so(identifier)

        if not so:
            return request.make_json_response(
                {'status': 'error', 'message': 'Sale Order not found'},
                status=404
            )

        allowed_fields = {
            'partner_id',
            'date_order',
            'note',
        }

        safe_payload = {k: v for k, v in payload.items() if k in allowed_fields}

        if not safe_payload:
            return request.make_json_response(
                {'status': 'error', 'message': 'No valid fields to update'},
                status=400
            )

        so.write(safe_payload)

        return request.make_json_response(
            {'status': 'success', 'message': 'Sale Order partially updated'}
        )

    # ===================================================
    # DELETE → Delete Sale Order
    # ===================================================
    @http.route('/api/v2/sales/<string:identifier>', type='http',
                auth='user', methods=['DELETE'], csrf=False)
    def delete_sale(self, identifier, **kwargs):
        so = self._get_so(identifier)

        if not so:
            return request.make_json_response(
                {'status': 'error', 'message': 'Sale Order not found'},
                status=404
            )

        so.unlink()

        return request.make_json_response(
            {'status': 'success', 'message': 'Sale Order deleted'}
        )

    # ===================================================
    # OPTIONS → API Metadata
    # ===================================================
    @http.route('/api/v2/sales', type='http',
                auth='user', methods=['OPTIONS'], csrf=False)
    def options_sales(self, **kwargs):
        info = {
            'collection': {
                'endpoint': '/api/v2/sales',
                'methods': ['GET', 'POST', 'OPTIONS'],
            },
            'single_resource': {
                'endpoint': '/api/v2/sales/<id_or_name>',
                'methods': ['GET', 'PUT', 'PATCH', 'DELETE'],
            },
            'version': 'v2'
        }

        return request.make_json_response({'status': 'success', 'info': info})
