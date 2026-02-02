# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class InventoryRestAPI(http.Controller):

    # ---------------------------------------------------
    # Helper → Get Picking by ID or NAME
    # ---------------------------------------------------
    def _get_picking(self, identifier):
        Picking = request.env['stock.picking'].sudo()

        if str(identifier).isdigit():
            picking = Picking.browse(int(identifier))
            if picking.exists():
                return picking

        return Picking.search([('name', '=', identifier)], limit=1)

    # ===================================================
    # GET → All Pickings
    # ===================================================
    @http.route('/api/v2/inventory', type='http', auth='user',
                methods=['GET'], csrf=False)
    def get_pickings(self, **kwargs):
        pickings = request.env['stock.picking'].sudo().search([])

        data = [{
            'id': p.id,
            'name': p.name,
            'partner': p.partner_id.name if p.partner_id else None,
            'state': p.state,
            'picking_type': p.picking_type_id.name,
            'scheduled_date': p.scheduled_date,
        } for p in pickings]

        return request.make_json_response({
            'status': 'success',
            'count': len(data),
            'data': data
        })

    # ===================================================
    # GET → Single Picking
    # ===================================================
    @http.route('/api/v2/inventory/<string:identifier>', type='http',
                auth='user', methods=['GET'], csrf=False)
    def get_picking(self, identifier, **kwargs):
        picking = self._get_picking(identifier)

        if not picking:
            return request.make_json_response(
                {'status': 'error', 'message': 'Picking not found'},
                status=404
            )

        data = {
            'id': picking.id,
            'name': picking.name,
            'state': picking.state,
            'partner': picking.partner_id.name if picking.partner_id else None,
            'picking_type': picking.picking_type_id.name,
            'source_location': picking.location_id.complete_name,
            'destination_location': picking.location_dest_id.complete_name,
            'moves': [{
                'move_id': m.id,
                'product_id': m.product_id.id,
                'product': m.product_id.name,
                'quantity': m.product_uom_qty,
                'done_qty': m.quantity_done,
            } for m in picking.move_ids_without_package]
        }

        return request.make_json_response({'status': 'success', 'data': data})

    # ===================================================
    # POST → Create Picking
    # ===================================================
    @http.route('/api/v2/inventory', type='http', auth='user',
                methods=['POST'], csrf=False)
    def create_picking(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.data or '{}')

            required_fields = [
                'picking_type_id',
                'location_id',
                'location_dest_id',
                'moves'
            ]

            for field in required_fields:
                if not payload.get(field):
                    return request.make_json_response(
                        {'status': 'error', 'message': f'{field} is required'},
                        status=400
                    )

            moves = []
            for move in payload['moves']:
                product = request.env['product.product'].sudo().browse(move['product_id'])
                if not product.exists():
                    return request.make_json_response(
                        {'status': 'error', 'message': f"Invalid product_id {move['product_id']}"},
                        status=400
                    )

                moves.append((0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': move.get('quantity', 1),
                    'product_uom': product.uom_id.id,
                    'location_id': payload['location_id'],
                    'location_dest_id': payload['location_dest_id'],
                }))

            picking = request.env['stock.picking'].sudo().create({
                'partner_id': payload.get('partner_id'),
                'picking_type_id': payload['picking_type_id'],
                'location_id': payload['location_id'],
                'location_dest_id': payload['location_dest_id'],
                'move_ids_without_package': moves,
            })

            return request.make_json_response(
                {'status': 'success', 'id': picking.id, 'name': picking.name},
                status=201
            )

        except Exception as e:
            _logger.exception("Error creating picking")
            return request.make_json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )

    # ===================================================
    # PUT → Update Moves (Draft Only)
    # ===================================================
    @http.route('/api/v2/inventory/<string:identifier>', type='http',
                auth='user', methods=['PUT'], csrf=False)
    def update_picking(self, identifier, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        picking = self._get_picking(identifier)

        if not picking:
            return request.make_json_response(
                {'status': 'error', 'message': 'Picking not found'},
                status=404
            )

        if picking.state != 'draft':
            return request.make_json_response(
                {'status': 'error', 'message': 'Only draft pickings can be updated'},
                status=400
            )

        commands = []

        for line in payload.get('update_moves', []):
            commands.append((1, line['move_id'], {
                'product_uom_qty': line.get('quantity'),
            }))

        for line in payload.get('new_moves', []):
            product = request.env['product.product'].sudo().browse(line['product_id'])
            commands.append((0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': line.get('quantity', 1),
                'product_uom': product.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
            }))

        for move_id in payload.get('delete_moves', []):
            commands.append((2, move_id, 0))

        if commands:
            picking.write({'move_ids_without_package': commands})

        return request.make_json_response(
            {'status': 'success', 'message': 'Picking updated'}
        )

    # ===================================================
    # PATCH → Validate / Mark Done
    # ===================================================
    @http.route('/api/v2/inventory/<string:identifier>/validate',
                type='http', auth='user', methods=['PATCH'], csrf=False)
    def validate_picking(self, identifier, **kwargs):
        picking = self._get_picking(identifier)

        if not picking:
            return request.make_json_response(
                {'status': 'error', 'message': 'Picking not found'},
                status=404
            )

        picking.action_confirm()
        picking.action_assign()

        for move in picking.move_ids_without_package:
            move.quantity_done = move.product_uom_qty

        picking.button_validate()

        return request.make_json_response(
            {'status': 'success', 'message': 'Picking validated'}
        )

    # ===================================================
    # DELETE → Delete Picking (Draft Only)
    # ===================================================
    @http.route('/api/v2/inventory/<string:identifier>', type='http',
                auth='user', methods=['DELETE'], csrf=False)
    def delete_picking(self, identifier, **kwargs):
        picking = self._get_picking(identifier)

        if not picking:
            return request.make_json_response(
                {'status': 'error', 'message': 'Picking not found'},
                status=404
            )

        if picking.state != 'draft':
            return request.make_json_response(
                {'status': 'error', 'message': 'Only draft pickings can be deleted'},
                status=400
            )

        picking.unlink()

        return request.make_json_response(
            {'status': 'success', 'message': 'Picking deleted'}
        )

    # ===================================================
    # OPTIONS → API Metadata
    # ===================================================
    @http.route('/api/v2/inventory', type='http',
                auth='user', methods=['OPTIONS'], csrf=False)
    def options_inventory(self, **kwargs):
        info = {
            'collection': {
                'endpoint': '/api/v2/inventory',
                'methods': ['GET', 'POST', 'OPTIONS'],
            },
            'single_resource': {
                'endpoint': '/api/v2/inventory/<id_or_name>',
                'methods': ['GET', 'PUT', 'PATCH', 'DELETE'],
            },
            'version': 'v2'
        }

        return request.make_json_response({'status': 'success', 'info': info})
