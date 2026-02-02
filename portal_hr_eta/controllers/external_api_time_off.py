# -*- coding: utf-8 -*-

import json
import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TimeOffRestAPI(http.Controller):

    # ===================================================
    # GET → All Time Off Requests
    # ===================================================
    @http.route('/api/v2/time_off', type='http', auth='user', methods=['GET'], csrf=False)
    def get_time_off(self, **kwargs):
        leaves = request.env['hr.leave'].sudo().search([])
        data = [{
            'id': l.id,
            'employee': l.employee_id.name,
            'employee_id': l.employee_id.id,
            'leave_type': l.holiday_status_id.name,
            'leave_type_id': l.holiday_status_id.id,
            'date_from': l.date_from,
            'date_to': l.date_to,
            'state': l.state,
            'days': l.number_of_days,
        } for l in leaves]

        return request.make_json_response({'status': 'success', 'data': data})

    # ===================================================
    # GET → Single Time Off
    # ===================================================
    @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_single_time_off(self, leave_id, **kwargs):
        leave = request.env['hr.leave'].sudo().browse(leave_id)

        if not leave.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Time off not found'},
                status=404
            )

        data = {
            'id': leave.id,
            'employee': leave.employee_id.name,
            'leave_type': leave.holiday_status_id.name,
            'date_from': leave.date_from,
            'date_to': leave.date_to,
            'state': leave.state,
            'days': leave.number_of_days,
        }

        return request.make_json_response({'status': 'success', 'data': data})

    # ===================================================
    # HEAD → Check if Time Off exists
    # ===================================================
    @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['HEAD'], csrf=False)
    def head_time_off(self, leave_id, **kwargs):
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        return ('', 200) if leave.exists() else ('', 404)

    # ===================================================
    # POST → Create Time Off (JSON ONLY)
    # ===================================================
    @http.route('/api/v2/time_off', type='http', auth='user', methods=['POST'], csrf=False)
    def create_time_off(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.data or '{}')

            required_fields = {'employee_id', 'holiday_status_id', 'date_from', 'date_to'}
            if not required_fields.issubset(payload):
                return request.make_json_response(
                    {'status': 'error', 'message': 'Missing required fields'},
                    status=400
                )

            leave = request.env['hr.leave'].sudo().create({
                'employee_id': payload['employee_id'],
                'holiday_status_id': payload['holiday_status_id'],
                'date_from': payload['date_from'],
                'date_to': payload['date_to'],
                'name': payload.get('name', 'Time Off Request'),
            })

            return request.make_json_response(
                {'status': 'success', 'id': leave.id},
                status=201
            )

        except Exception:
            _logger.exception("Error creating time off")
            return request.make_json_response(
                {'status': 'error', 'message': 'Internal server error'},
                status=500
            )

    # ===================================================
    # PUT → Full Update Time Off
    # ===================================================
    @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def put_time_off(self, leave_id, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        leave = request.env['hr.leave'].sudo().browse(leave_id)

        if not leave.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Time off not found'},
                status=404
            )

        data = {
            'employee_id': payload.get('employee_id'),
            'holiday_status_id': payload.get('holiday_status_id'),
            'date_from': payload.get('date_from'),
            'date_to': payload.get('date_to'),
            'name': payload.get('name'),
        }

        leave.write({k: v for k, v in data.items() if v is not None})

        return request.make_json_response(
            {'status': 'success', 'message': 'Time off fully updated'}
        )

    # ===================================================
    # PATCH → Partial Update Time Off
    # ===================================================
    @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['PATCH'], csrf=False)
    def patch_time_off(self, leave_id, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        leave = request.env['hr.leave'].sudo().browse(leave_id)

        if not leave.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Time off not found'},
                status=404
            )

        allowed_fields = {'name', 'date_from', 'date_to', 'holiday_status_id'}
        safe_payload = {k: v for k, v in payload.items() if k in allowed_fields}

        if not safe_payload:
            return request.make_json_response(
                {'status': 'error', 'message': 'No valid fields to update'},
                status=400
            )

        leave.write(safe_payload)

        return request.make_json_response(
            {'status': 'success', 'message': 'Time off partially updated'}
        )

    # ===================================================
    # DELETE → Delete Time Off
    # ===================================================
    @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_time_off(self, leave_id, **kwargs):
        leave = request.env['hr.leave'].sudo().browse(leave_id)

        if not leave.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Time off not found'},
                status=404
            )

        leave.unlink()

        return request.make_json_response(
            {'status': 'success', 'message': 'Time off deleted'}
        )


# ===================================================
# ATTACHMENTS FOR TIME OFF (CRUD)
# ===================================================

class TimeOffAttachmentAPI(http.Controller):

    # ===================================================
    # GET → List attachments
    # ===================================================
    @http.route('/api/v2/time_off/<int:leave_id>/attachments',
                type='http', auth='user', methods=['GET'], csrf=False)
    def list_attachments(self, leave_id, **kwargs):
        attachments = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'hr.leave'),
            ('res_id', '=', leave_id)
        ])

        data = [{
            'id': att.id,
            'name': att.name,
            'mimetype': att.mimetype,
            'size': att.file_size,
            'created_on': att.create_date,
        } for att in attachments]

        return request.make_json_response({'status': 'success', 'data': data})

    # ===================================================
    # POST → Upload attachment
    # ===================================================
    @http.route('/api/v2/time_off/<int:leave_id>/attachments',
                type='http', auth='user', methods=['POST'], csrf=False)
    def upload_attachment(self, leave_id, **kwargs):
        file = request.httprequest.files.get('file')

        if not file:
            return request.make_json_response(
                {'status': 'error', 'message': 'File is required'},
                status=400
            )

        attachment = request.env['ir.attachment'].sudo().create({
            'name': file.filename,
            'datas': base64.b64encode(file.read()),
            'res_model': 'hr.leave',
            'res_id': leave_id,
            'mimetype': file.content_type,
        })

        return request.make_json_response(
            {'status': 'success', 'attachment_id': attachment.id},
            status=201
        )

    # ===================================================
    # GET → Download attachment
    # ===================================================
    @http.route('/api/v2/time_off/<int:leave_id>/attachments/<int:attachment_id>',
                type='http', auth='user', methods=['GET'], csrf=False)
    def download_attachment(self, leave_id, attachment_id, **kwargs):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)

        if not attachment.exists() or attachment.res_id != leave_id:
            return request.make_json_response(
                {'status': 'error', 'message': 'Attachment not found'},
                status=404
            )

        file_data = base64.b64decode(attachment.datas)
        headers = [
            ('Content-Type', attachment.mimetype or 'application/octet-stream'),
            ('Content-Disposition', f'attachment; filename="{attachment.name}"')
        ]

        return request.make_response(file_data, headers)

    # ===================================================
    # DELETE → Remove attachment
    # ===================================================
    @http.route('/api/v2/time_off/<int:leave_id>/attachments/<int:attachment_id>',
                type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_attachment(self, leave_id, attachment_id, **kwargs):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)

        if not attachment.exists() or attachment.res_id != leave_id:
            return request.make_json_response(
                {'status': 'error', 'message': 'Attachment not found'},
                status=404
            )

        attachment.unlink()

        return request.make_json_response(
            {'status': 'success', 'message': 'Attachment deleted'}
        )
















# # -*- coding: utf-8 -*-
#
# import json
# import logging
#
# from odoo import http
# from odoo.http import request
#
# _logger = logging.getLogger(__name__)
#
#
# class TimeOffRestAPI(http.Controller):
#
#     # ===================================================
#     # GET → All Time Off Requests
#     # ===================================================
#     @http.route('/api/v2/time_off', type='http', auth='user', methods=['GET'], csrf=False)
#     def get_time_off(self, **kwargs):
#         leaves = request.env['hr.leave'].sudo().search([])
#         data = [{
#             'id': l.id,
#             'employee': l.employee_id.name,
#             'employee_id': l.employee_id.id,
#             'leave_type': l.holiday_status_id.name,
#             'leave_type_id': l.holiday_status_id.id,
#             'date_from': l.date_from,
#             'date_to': l.date_to,
#             'state': l.state,
#             'days': l.number_of_days,
#         } for l in leaves]
#
#         return request.make_json_response({'status': 'success', 'data': data})
#
#     # ===================================================
#     # GET → Single Time Off
#     # ===================================================
#     @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['GET'], csrf=False)
#     def get_single_time_off(self, leave_id, **kwargs):
#         leave = request.env['hr.leave'].sudo().browse(leave_id)
#
#         if not leave.exists():
#             return request.make_json_response(
#                 {'status': 'error', 'message': 'Time off not found'},
#                 status=404
#             )
#
#         data = {
#             'id': leave.id,
#             'employee': leave.employee_id.name,
#             'leave_type': leave.holiday_status_id.name,
#             'date_from': leave.date_from,
#             'date_to': leave.date_to,
#             'state': leave.state,
#             'days': leave.number_of_days,
#         }
#
#         return request.make_json_response({'status': 'success', 'data': data})
#
#     # ===================================================
#     # HEAD → Check if Time Off exists
#     # ===================================================
#     @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['HEAD'], csrf=False)
#     def head_time_off(self, leave_id, **kwargs):
#         leave = request.env['hr.leave'].sudo().browse(leave_id)
#         return ('', 200) if leave.exists() else ('', 404)
#
#     # ===================================================
#     # POST → Create Time Off
#     # ===================================================
#     @http.route('/api/v2/time_off', type='http', auth='user', methods=['POST'], csrf=False)
#     def create_time_off(self, **kwargs):
#         try:
#             payload = json.loads(request.httprequest.data or '{}')
#
#             required_fields = {'employee_id', 'holiday_status_id', 'date_from', 'date_to'}
#             if not required_fields.issubset(payload):
#                 return request.make_json_response(
#                     {'status': 'error', 'message': 'Missing required fields'},
#                     status=400
#                 )
#
#             leave = request.env['hr.leave'].sudo().create({
#                 'employee_id': payload['employee_id'],
#                 'holiday_status_id': payload['holiday_status_id'],
#                 'date_from': payload['date_from'],
#                 'date_to': payload['date_to'],
#                 'name': payload.get('name', 'Time Off Request'),
#             })
#
#             return request.make_json_response(
#                 {'status': 'success', 'id': leave.id},
#                 status=201
#             )
#
#         except Exception:
#             _logger.exception("Error creating time off")
#             return request.make_json_response(
#                 {'status': 'error', 'message': 'Internal server error'},
#                 status=500
#             )
#
#     # ===================================================
#     # PUT → Full Update Time Off (SAFE)
#     # ===================================================
#     @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['PUT'], csrf=False)
#     def put_time_off(self, leave_id, **kwargs):
#         payload = json.loads(request.httprequest.data or '{}')
#         leave = request.env['hr.leave'].sudo().browse(leave_id)
#
#         if not leave.exists():
#             return request.make_json_response(
#                 {'status': 'error', 'message': 'Time off not found'},
#                 status=404
#             )
#
#         data = {
#             'employee_id': payload.get('employee_id'),
#             'holiday_status_id': payload.get('holiday_status_id'),
#             'date_from': payload.get('date_from'),
#             'date_to': payload.get('date_to'),
#             'name': payload.get('name'),
#         }
#
#         leave.write({k: v for k, v in data.items() if v is not None})
#
#         return request.make_json_response(
#             {'status': 'success', 'message': 'Time off fully updated'}
#         )
#
#     # ===================================================
#     # PATCH → Partial Update Time Off (SECURE)
#     # ===================================================
#     @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['PATCH'], csrf=False)
#     def patch_time_off(self, leave_id, **kwargs):
#         payload = json.loads(request.httprequest.data or '{}')
#         leave = request.env['hr.leave'].sudo().browse(leave_id)
#
#         if not leave.exists():
#             return request.make_json_response(
#                 {'status': 'error', 'message': 'Time off not found'},
#                 status=404
#             )
#
#         allowed_fields = {
#             'name',
#             'date_from',
#             'date_to',
#             'holiday_status_id'
#         }
#
#         safe_payload = {k: v for k, v in payload.items() if k in allowed_fields}
#
#         if not safe_payload:
#             return request.make_json_response(
#                 {'status': 'error', 'message': 'No valid fields to update'},
#                 status=400
#             )
#
#         leave.write(safe_payload)
#
#         return request.make_json_response(
#             {'status': 'success', 'message': 'Time off partially updated'}
#         )
#
#     # ===================================================
#     # DELETE → Delete Time Off
#     # ===================================================
#     @http.route('/api/v2/time_off/<int:leave_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
#     def delete_time_off(self, leave_id, **kwargs):
#         leave = request.env['hr.leave'].sudo().browse(leave_id)
#
#         if not leave.exists():
#             return request.make_json_response(
#                 {'status': 'error', 'message': 'Time off not found'},
#                 status=404
#             )
#
#         leave.unlink()
#
#         return request.make_json_response(
#             {'status': 'success', 'message': 'Time off deleted'}
#         )
#
#     # ===================================================
#     # OPTIONS → Time Off API Metadata
#     # ===================================================
#     @http.route('/api/v2/time_off', type='http', auth='user', methods=['OPTIONS'], csrf=False)
#     def options_time_off(self, **kwargs):
#         info = {
#             'collection': {
#                 'endpoint': '/api/v2/time_off',
#                 'methods': ['GET', 'POST', 'OPTIONS'],
#             },
#             'single_resource': {
#                 'endpoint': '/api/v2/time_off/<leave_id>',
#                 'methods': ['GET', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'],
#             },
#             'version': 'v2'
#         }
#
#         return request.make_json_response({'status': 'success', 'info': info})
