# -*- coding: utf-8 -*-

import json
import base64
import logging

from odoo import http
from odoo.http import request
import base64

_logger = logging.getLogger(__name__)


class EmployeeRestAPI(http.Controller):

    # ===================================================
    # GET → All Employees
    # ===================================================
    @http.route('/api/v2/employees', type='http', auth='user', methods=['GET'], csrf=False)
    def get_employees(self, **kwargs):
        employees = request.env['hr.employee'].sudo().search([])
        data = [{
            'id': e.id,
            'name': e.name,
            'job_title': e.job_title,
            'work_email': e.work_email,
            'work_phone': e.work_phone,
            'department': e.department_id.name if e.department_id else None,
        } for e in employees]

        return request.make_json_response({'status': 'success', 'data': data})

    # ===================================================
    # GET → Single Employee
    # ===================================================
    @http.route('/api/v2/employees/<int:employee_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_employee(self, employee_id, **kwargs):
        employee = request.env['hr.employee'].sudo().browse(employee_id)

        if not employee.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Employee not found'},
                status=404
            )

        data = {
            'id': employee.id,
            'name': employee.name,
            'job_title': employee.job_title,
            'work_email': employee.work_email,
            'work_phone': employee.work_phone,
            'department': employee.department_id.name if employee.department_id else None,
        }

        return request.make_json_response({'status': 'success', 'data': data})

    # ===================================================
    # POST → Create Employee with Image
    # ===================================================
    @http.route('/api/v2/employees', type='http', auth='user', methods=['POST', 'PATCH'], csrf=False)
    def create_employee(self, **kwargs):
        try:
            # 1️⃣ Read form fields (NOT JSON)
            name = kwargs.get('name')
            job_title = kwargs.get('job_title')
            work_email = kwargs.get('work_email')
            work_phone = kwargs.get('work_phone')
            department_id = kwargs.get('department_id')

            if not name:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Name is required'},
                    status=400
                )

            # 2️⃣ Read image file
            file = request.httprequest.files.get('image')

            if not file:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Image is required'},
                    status=400
                )

            image_base64 = base64.b64encode(file.read())

            # 3️⃣ Create employee (ONCE, safely)
            employee = request.env['hr.employee'].sudo().create({
                'name': name,
                'job_title': job_title,
                'work_email': work_email,
                'work_phone': work_phone,
                'department_id': int(department_id) if department_id else False,
                'image_1920': image_base64,
            })

            return request.make_json_response(
                {'status': 'success', 'id': employee.id},
                status=201
            )

        except Exception:
            _logger.exception("Error creating employee")
            return request.make_json_response(
                {'status': 'error', 'message': 'Internal server error'},
                status=500
            )

    # ===================================================
    # PUT → Full Update Employee (JSON ONLY)
    # ===================================================
    @http.route('/api/v2/employees/<int:employee_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def put_employee(self, employee_id, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        employee = request.env['hr.employee'].sudo().browse(employee_id)

        if not employee.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Employee not found'},
                status=404
            )

        data = {
            'name': payload.get('name'),
            'job_title': payload.get('job_title'),
            'work_email': payload.get('work_email'),
            'work_phone': payload.get('work_phone'),
            'department_id': payload.get('department_id'),
        }

        employee.write({k: v for k, v in data.items() if v is not None})

        return request.make_json_response(
            {'status': 'success', 'message': 'Employee fully updated'}
        )

    # ===================================================
    # PATCH → Partial Update Employee (JSON ONLY)
    # ===================================================
    @http.route('/api/v2/employees/<int:employee_id>', type='http', auth='user', methods=['PATCH'], csrf=False)
    def patch_employee(self, employee_id, **kwargs):
        payload = json.loads(request.httprequest.data or '{}')
        employee = request.env['hr.employee'].sudo().browse(employee_id)

        if not employee.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Employee not found'},
                status=404
            )

        allowed_fields = {
            'name',
            'job_title',
            'work_email',
            'work_phone',
            'department_id',
        }

        safe_payload = {k: v for k, v in payload.items() if k in allowed_fields}

        if not safe_payload:
            return request.make_json_response(
                {'status': 'error', 'message': 'No valid fields to update'},
                status=400
            )

        employee.write(safe_payload)

        return request.make_json_response(
            {'status': 'success', 'message': 'Employee partially updated'}
        )

    # ===================================================
    # DELETE → Delete Employee
    # ===================================================
    @http.route('/api/v2/employees/<int:employee_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_employee(self, employee_id, **kwargs):
        employee = request.env['hr.employee'].sudo().browse(employee_id)

        if not employee.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Employee not found'},
                status=404
            )

        employee.unlink()

        return request.make_json_response(
            {'status': 'success', 'message': 'Employee deleted'}
        )

    # ===================================================
    # PUT → Upload / Update Employee Image (FILE ONLY)
    # ===================================================
    @http.route('/api/v2/employees/<int:employee_id>/image', type='http',
                auth='user', methods=['PUT', 'POST'], csrf=False)
    def update_employee_image(self, employee_id, **kwargs):
        employee = request.env['hr.employee'].sudo().browse(employee_id)

        if not employee.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Employee not found'},
                status=404
            )

        file = request.httprequest.files.get('image')

        if not file:
            return request.make_json_response(
                {'status': 'error', 'message': 'Image file is required'},
                status=400
            )

        image_base64 = base64.b64encode(file.read())

        employee.write({'image_1920': image_base64})

        return request.make_json_response(
            {'status': 'success', 'message': 'Employee image updated'}
        )

    # ===================================================
    # DELETE → Remove Employee Image
    # ===================================================
    @http.route('/api/v2/employees/<int:employee_id>/image', type='http',
                auth='user', methods=['DELETE'], csrf=False)
    def delete_employee_image(self, employee_id, **kwargs):
        employee = request.env['hr.employee'].sudo().browse(employee_id)

        if not employee.exists():
            return request.make_json_response(
                {'status': 'error', 'message': 'Employee not found'},
                status=404
            )

        employee.write({'image_1920': False})

        return request.make_json_response(
            {'status': 'success', 'message': 'Employee image removed'}
        )

    # ===================================================
    # OPTIONS → API Metadata
    # ===================================================
    @http.route('/api/v2/employees', type='http', auth='user', methods=['OPTIONS'], csrf=False)
    def options_employees(self, **kwargs):
        info = {
            'collection': {
                'endpoint': '/api/v2/employees',
                'methods': ['GET', 'POST', 'OPTIONS'],
            },
            'single_resource': {
                'endpoint': '/api/v2/employees/<employee_id>',
                'methods': ['GET', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
            },
            'image_resource': {
                'endpoint': '/api/v2/employees/<employee_id>/image',
                'methods': ['PUT', 'POST', 'DELETE'],
            },
            'version': 'v2'
        }

        return request.make_json_response({'status': 'success', 'info': info})
