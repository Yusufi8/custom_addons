# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PurchaseOrderRestAPI(http.Controller):

    # ---------------------------------------------------
    # Helper → Get Purchase Order by ID or NAME
    # ---------------------------------------------------
    def _get_po(self, identifier):
        PurchaseOrder = request.env['purchase.order'].sudo()

        # Try numeric ID
        if str(identifier).isdigit():
            po = PurchaseOrder.browse(int(identifier))
            if po.exists():
                return po

        # Fallback to PO number (name)
        return PurchaseOrder.search([('name', '=', identifier)], limit=1)

    # ===================================================
    # GET → All Purchase Orders (LIKE EMPLOYEES)
    # ===================================================
    @http.route('/api/v2/purchases', type='http', auth='user',
                methods=['GET'], csrf=False)
    def get_purchases(self, **kwargs):
        purchases = request.env['purchase.order'].sudo().search([])

        data = [{
            'id': po.id,
            'name': po.name,
            'vendor': po.partner_id.name if po.partner_id else None,
            'state': po.state,
            'date_order': po.date_order,
            'amount_total': po.amount_total,
            'currency': po.currency_id.name if po.currency_id else None,
        } for po in purchases]

        return request.make_json_response({
            'status': 'success',
            'count': len(data),
            'data': data
        })

    # ===================================================
    # GET → Single Purchase Order (ID or NAME)
    # ===================================================
    @http.route('/api/v2/purchases/<string:identifier>', type='http',
                auth='user', methods=['GET'], csrf=False)
    def get_purchase(self, identifier, **kwargs):
        po = self._get_po(identifier)

        if not po:
            return request.make_json_response(
                {'status': 'error', 'message': 'Purchase Order not found'},
                status=404
            )

        data = {
            'id': po.id,
            'name': po.name,
            'vendor': po.partner_id.name if po.partner_id else None,
            'state': po.state,
            'date_order': po.date_order,
            'amount_total': po.amount_total,
            'lines': [{
                'line_id': l.id,
                'product_id': l.product_id.id,
                'product': l.product_id.name,
                'quantity': l.product_qty,
                'price_unit': l.price_unit,
                'subtotal': l.price_subtotal,
            } for l in po.order_line]
        }

        return request.make_json_response({'status': 'success', 'data': data})

    # ===================================================
    # POST → Create Purchase Order
    # ===================================================
    @http.route('/api/v2/purchases', type='http', auth='user',
                methods=['POST'], csrf=False)
    def create_purchase(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.data or '{}')

            if not payload.get('partner_id') or not payload.get('order_lines'):
                return request.make_json_response(
                    {'status': 'error', 'message': 'partner_id and order_lines required'},
                    status=400
                )

            lines = []
            for line in payload['order_lines']:
                lines.append((0, 0, {
                    'product_id': line['product_id'],
                    'product_qty': line.get('quantity', 1),
                    'price_unit': line.get('price_unit', 0),
                    'date_planned': line.get('date_planned'),
                }))

            po = request.env['purchase.order'].sudo().create({
                'partner_id': payload['partner_id'],
                'order_line': lines,
            })

            return request.make_json_response(
                {'status': 'success', 'id': po.id, 'name': po.name},
                status=201
            )

        except Exception:
            _logger.exception("Error creating purchase order")
            return request.make_json_response(
                {'status': 'error', 'message': 'Internal server error'},
                status=500
            )

    # ===================================================
    # PUT → Full Update Purchase Order (LINES)
    # ===================================================
    @http.route('/api/v2/purchases/<string:identifier>', type='http',
                auth='user', methods=['PUT'], csrf=False)
    def put_purchase(self, identifier, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        po = self._get_po(identifier)

        if not po:
            return request.make_json_response(
                {'status': 'error', 'message': 'Purchase Order not found'},
                status=404
            )

        commands = []

        for line in payload.get('update_lines', []):
            commands.append((1, line['line_id'], {
                'product_qty': line.get('quantity'),
                'price_unit': line.get('price_unit'),
            }))

        for line in payload.get('new_lines', []):
            commands.append((0, 0, {
                'product_id': line['product_id'],
                'product_qty': line.get('quantity', 1),
                'price_unit': line.get('price_unit', 0),
                'date_planned': line.get('date_planned'),
            }))

        for line_id in payload.get('delete_lines', []):
            commands.append((2, line_id, 0))

        if commands:
            po.write({'order_line': commands})

        return request.make_json_response(
            {'status': 'success', 'message': 'Purchase Order updated'}
        )

    # ===================================================
    # PATCH → Partial Update Purchase Order (HEADER ONLY)
    # ===================================================
    @http.route('/api/v2/purchases/<string:identifier>', type='http',
                auth='user', methods=['PATCH'], csrf=False)
    def patch_purchase(self, identifier, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        po = self._get_po(identifier)

        if not po:
            return request.make_json_response(
                {'status': 'error', 'message': 'Purchase Order not found'},
                status=404
            )

        allowed_fields = {
            'partner_id',
            'date_order',
            'notes',
        }

        safe_payload = {k: v for k, v in payload.items() if k in allowed_fields}

        if not safe_payload:
            return request.make_json_response(
                {'status': 'error', 'message': 'No valid fields to update'},
                status=400
            )

        po.write(safe_payload)

        return request.make_json_response(
            {'status': 'success', 'message': 'Purchase Order partially updated'}
        )

    # ===================================================
    # DELETE → Delete Purchase Order
    # ===================================================
    @http.route('/api/v2/purchases/<string:identifier>', type='http',
                auth='user', methods=['DELETE'], csrf=False)
    def delete_purchase(self, identifier, **kwargs):
        po = self._get_po(identifier)

        if not po:
            return request.make_json_response(
                {'status': 'error', 'message': 'Purchase Order not found'},
                status=404
            )

        po.unlink()

        return request.make_json_response(
            {'status': 'success', 'message': 'Purchase Order deleted'}
        )

    # ===================================================
    # OPTIONS → API Metadata
    # ===================================================
    @http.route('/api/v2/purchases', type='http',
                auth='user', methods=['OPTIONS'], csrf=False)
    def options_purchases(self, **kwargs):
        info = {
            'collection': {
                'endpoint': '/api/v2/purchases',
                'methods': ['GET', 'POST', 'OPTIONS'],
            },
            'single_resource': {
                'endpoint': '/api/v2/purchases/<id_or_name>',
                'methods': ['GET', 'PUT', 'PATCH', 'DELETE'],
            },
            'version': 'v2'
        }

        return request.make_json_response({'status': 'success', 'info': info})
