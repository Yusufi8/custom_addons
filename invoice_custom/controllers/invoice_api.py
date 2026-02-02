# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class InvoiceRestAPI(http.Controller):

    # ---------------------------------------------------
    # Helper → Get Invoice by ID or NAME
    # ---------------------------------------------------
    def _get_invoice(self, identifier):
        Invoice = request.env['account.move'].sudo()

        if str(identifier).isdigit():
            inv = Invoice.browse(int(identifier))
            if inv.exists():
                return inv

        return Invoice.search([
            ('name', '=', identifier),
            ('move_type', '=', 'out_invoice')
        ], limit=1)

    # ===================================================
    # GET → All Invoices
    # ===================================================
    @http.route('/api/v2/invoices', type='http', auth='user',
                methods=['GET'], csrf=False)
    def get_invoices(self, **kwargs):
        invoices = request.env['account.move'].sudo().search([
            ('move_type', '=', 'out_invoice')
        ])

        data = [{
            'id': inv.id,
            'name': inv.name,
            'customer': inv.partner_id.name if inv.partner_id else None,
            'state': inv.state,
            'invoice_date': inv.invoice_date,
            'amount_total': inv.amount_total,
            'currency': inv.currency_id.name if inv.currency_id else None,
        } for inv in invoices]

        return request.make_json_response({
            'status': 'success',
            'count': len(data),
            'data': data
        })

    # ===================================================
    # GET → Single Invoice
    # ===================================================
    @http.route('/api/v2/invoices/<string:identifier>', type='http',
                auth='user', methods=['GET'], csrf=False)
    def get_invoice(self, identifier, **kwargs):
        inv = self._get_invoice(identifier)

        if not inv:
            return request.make_json_response(
                {'status': 'error', 'message': 'Invoice not found'},
                status=404
            )

        data = {
            'id': inv.id,
            'name': inv.name,
            'state': inv.state,
            'partner': inv.partner_id.name if inv.partner_id else None,
            'invoice_date': inv.invoice_date,
            'amount_total': inv.amount_total,
            'lines': [{
                'line_id': l.id,
                'product_id': l.product_id.id,
                'product': l.product_id.name,
                'quantity': l.quantity,
                'price_unit': l.price_unit,
                'subtotal': l.price_subtotal,
            } for l in inv.invoice_line_ids]
        }

        return request.make_json_response({'status': 'success', 'data': data})

    # ===================================================
    # POST → Create Invoice
    # ===================================================
    @http.route('/api/v2/invoices', type='http', auth='user',
                methods=['POST'], csrf=False)
    def create_invoice(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.data or '{}')

            if not payload.get('partner_id') or not payload.get('invoice_lines'):
                return request.make_json_response(
                    {'status': 'error', 'message': 'partner_id and invoice_lines required'},
                    status=400
                )

            partner = request.env['res.partner'].sudo().browse(payload['partner_id'])
            if not partner.exists():
                return request.make_json_response(
                    {'status': 'error', 'message': 'Invalid partner_id'},
                    status=400
                )

            lines = []
            for line in payload['invoice_lines']:
                product = request.env['product.product'].sudo().browse(line['product_id'])
                if not product.exists():
                    return request.make_json_response(
                        {'status': 'error', 'message': f"Invalid product_id {line['product_id']}"},
                        status=400
                    )

                lines.append((0, 0, {
                    'product_id': product.id,
                    'quantity': line.get('quantity', 1),
                    'price_unit': line.get('price_unit', product.lst_price),
                }))

            invoice = request.env['account.move'].sudo().create({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'invoice_line_ids': lines,
            })

            invoice.action_post()  # 🔥 REQUIRED

            return request.make_json_response(
                {'status': 'success', 'id': invoice.id, 'name': invoice.name},
                status=201
            )

        except Exception as e:
            _logger.exception("Error creating invoice")
            return request.make_json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )

    # ===================================================
    # PUT → Full Update Invoice (LINES)
    # ===================================================
    @http.route('/api/v2/invoices/<string:identifier>', type='http',
                auth='user', methods=['PUT'], csrf=False)
    def put_invoice(self, identifier, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        inv = self._get_invoice(identifier)

        if not inv:
            return request.make_json_response(
                {'status': 'error', 'message': 'Invoice not found'},
                status=404
            )

        if inv.state != 'draft':
            return request.make_json_response(
                {'status': 'error', 'message': 'Only draft invoices can be updated'},
                status=400
            )

        commands = []

        for line in payload.get('update_lines', []):
            commands.append((1, line['line_id'], {
                'quantity': line.get('quantity'),
                'price_unit': line.get('price_unit'),
            }))

        for line in payload.get('new_lines', []):
            commands.append((0, 0, {
                'product_id': line['product_id'],
                'quantity': line.get('quantity', 1),
                'price_unit': line.get('price_unit', 0),
            }))

        for line_id in payload.get('delete_lines', []):
            commands.append((2, line_id, 0))

        if commands:
            inv.write({'invoice_line_ids': commands})

        return request.make_json_response(
            {'status': 'success', 'message': 'Invoice updated'}
        )

    # ===================================================
    # PATCH → Partial Update Invoice (HEADER)
    # ===================================================
    @http.route('/api/v2/invoices/<string:identifier>', type='http',
                auth='user', methods=['PATCH'], csrf=False)
    def patch_invoice(self, identifier, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        inv = self._get_invoice(identifier)

        if not inv:
            return request.make_json_response(
                {'status': 'error', 'message': 'Invoice not found'},
                status=404
            )

        if inv.state != 'draft':
            return request.make_json_response(
                {'status': 'error', 'message': 'Only draft invoices can be updated'},
                status=400
            )

        allowed_fields = {
            'invoice_date',
            'invoice_payment_term_id',
            'narration',
        }

        safe_payload = {k: v for k, v in payload.items() if k in allowed_fields}

        if not safe_payload:
            return request.make_json_response(
                {'status': 'error', 'message': 'No valid fields to update'},
                status=400
            )

        inv.write(safe_payload)

        return request.make_json_response(
            {'status': 'success', 'message': 'Invoice partially updated'}
        )

    # ===================================================
    # DELETE → Delete Invoice
    # ===================================================
    @http.route('/api/v2/invoices/<string:identifier>', type='http',
                auth='user', methods=['DELETE'], csrf=False)
    def delete_invoice(self, identifier, **kwargs):
        inv = self._get_invoice(identifier)

        if not inv:
            return request.make_json_response(
                {'status': 'error', 'message': 'Invoice not found'},
                status=404
            )

        if inv.state != 'draft':
            return request.make_json_response(
                {'status': 'error', 'message': 'Only draft invoices can be deleted'},
                status=400
            )

        inv.unlink()

        return request.make_json_response(
            {'status': 'success', 'message': 'Invoice deleted'}
        )

    # ===================================================
    # OPTIONS → API Metadata
    # ===================================================
    @http.route('/api/v2/invoices', type='http',
                auth='user', methods=['OPTIONS'], csrf=False)
    def options_invoices(self, **kwargs):
        info = {
            'collection': {
                'endpoint': '/api/v2/invoices',
                'methods': ['GET', 'POST', 'OPTIONS'],
            },
            'single_resource': {
                'endpoint': '/api/v2/invoices/<id_or_name>',
                'methods': ['GET', 'PUT', 'PATCH', 'DELETE'],
            },
            'version': 'v2'
        }

        return request.make_json_response({'status': 'success', 'info': info})
