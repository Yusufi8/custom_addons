import math
import re
import base64
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.exceptions import AccessError


class PortalEmployees(http.Controller):

    # =====================================================
    # EMPLOYEE LIST
    # =====================================================
    @http.route('/my/employees', type='http', auth='user', website=True)
    def portal_employees_list(self, page=1, search='', **kw):
        user = request.env.user
        Employee = request.env['hr.employee']

        domain = [('company_id', '=', user.company_id.id)]

        if search:
            domain += ['|', '|',
                ('name', 'ilike', search),
                ('job_title', 'ilike', search),
                ('work_email', 'ilike', search),
            ]

        total = Employee.search_count(domain)
        limit = 10

        pager = portal_pager(
            url='/my/employees',
            total=total,
            page=page,
            step=limit,
            url_args={'search': search},
        )

        employees = Employee.search(
            domain,
            order='name asc',
            limit=limit,
            offset=pager['offset'],
        )

        return request.render('portal_hr_eta.portal_employees_list', {
            'employees': employees,
            'pager': pager,
            'search': search,
            'page_name': 'employees',
        })

    # =====================================================
    # EMPLOYEE DETAIL
    # =====================================================
    @http.route('/my/employees/<int:employee_id>', type='http', auth='user', website=True)
    def portal_employee_detail(self, employee_id):
        user = request.env.user
        Employee = request.env['hr.employee']

        employee = Employee.browse(employee_id)

        if not employee.exists() or employee.company_id != user.company_id:
            raise AccessError(_("You are not allowed to view this employee."))

        ids = Employee.search(
            [('company_id', '=', user.company_id.id)],
            order='name asc'
        ).ids

        form_pager = None
        if employee.id in ids:
            index = ids.index(employee.id)
            form_pager = {
                'prev_url': f'/my/employees/{ids[index - 1]}' if index > 0 else None,
                'next_url': f'/my/employees/{ids[index + 1]}' if index < len(ids) - 1 else None,
                'index': index + 1,
                'total': len(ids),
            }

        return request.render('portal_hr_eta.portal_employee_form', {
            'employee': employee,
            'form_pager': form_pager,
            'page_name': 'employees',
        })


# class PortalEmployees(http.Controller):
#
#     @http.route('/my/employees', type='http', auth='user', website=True)
#     def portal_employees_list(self, **kw):
#         # pagination parameters
#         try:
#             page = int(kw.get('page', 1))
#             if page < 1:
#                 page = 1
#         except (TypeError, ValueError):
#             page = 1
#
#         limit = 10
#         offset = (page - 1) * limit
#
#         domain = []
#         Employee = request.env['hr.employee'].sudo()
#         total = Employee.search_count(domain)
#
#         employees = Employee.search(domain, limit=limit, offset=offset)
#
#         # build a minimal pager dict compatible with portal templates
#         page_count = int(math.ceil(float(total) / limit)) if total else 1
#
#         def _get_url(p):
#             return "%s?page=%s" % ("/my/employees", p) if p > 1 else "/my/employees"
#
#         pager_obj = {
#             'page_count': page_count,
#             'offset': offset,
#             'page': {'url': _get_url(page), 'num': page},
#             'page_first': {'url': _get_url(1), 'num': 1},
#             'page_previous': {'url': _get_url(max(1, page - 1)), 'num': max(1, page - 1)},
#             'page_next': {'url': _get_url(page + 1 if page + 1 <= page_count else page_count), 'num': page + 1 if page + 1 <= page_count else page_count},
#             'page_last': {'url': _get_url(page_count), 'num': page_count},
#             'pages': [{'url': _get_url(p), 'num': p} for p in range(1, page_count + 1)],
#         }
#
#         return request.render(
#             'portal_hr_eta.portal_employees_list',
#             {
#                 'employees': employees,
#                 'pager': pager_obj,
#                 'page': page,
#                 'limit': limit,
#                 'total': total,
#             }
#         )
#
#     @http.route('/my/employees/<int:employee_id>', type='http', auth='user', website=True)
#     def portal_employee_form(self, employee_id):
#         employee = request.env['hr.employee'].sudo().browse(employee_id)
#
#         if not employee.exists():
#             return request.not_found()
#
#         # build form-level pager (prev/next) across all employees
#         Employee = request.env['hr.employee'].sudo()
#         all_ids = Employee.search([], order='name').ids
#         form_pager = None
#         if employee.id in all_ids:
#             idx = all_ids.index(employee.id)
#             prev_id = all_ids[idx - 1] if idx > 0 else None
#             next_id = all_ids[idx + 1] if idx < len(all_ids) - 1 else None
#             form_pager = {
#                 'prev_url': f"/my/employees/{prev_id}" if prev_id else None,
#                 'next_url': f"/my/employees/{next_id}" if next_id else None,
#                 'index': idx + 1,
#                 'total': len(all_ids),
#             }
#
#         return request.render(
#             'portal_hr_eta.portal_employee_form',
#             {
#                 'employee': employee,
#                 'form_pager': form_pager,
#             }
#         )
