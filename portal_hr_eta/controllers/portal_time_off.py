import math
import re
import base64
from werkzeug import urls

from odoo import http, tools, _, SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError, MissingError, UserError, ValidationError
from odoo.http import content_disposition, Controller, request, route
from odoo.tools import consteq
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager





class PortalTimeOff(http.Controller):

    # =================================================
    # My Time Off (List)
    # =================================================
    @http.route('/my/timeoff', type='http', auth='user', website=True)
    def portal_my_timeoff(self, **kw):
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        if not employee:
            raise AccessError()

        # pagination
        try:
            page = int(kw.get('page', 1))
            if page < 1:
                page = 1
        except (TypeError, ValueError):
            page = 1
        # page_size optional override for testing: ?page_size=5
        try:
            page_size = int(kw.get('page_size')) if kw.get('page_size') else None
            if page_size and (page_size < 1 or page_size > 100):
                page_size = None
        except (TypeError, ValueError):
            page_size = None
        limit = page_size or 10
        offset = (page - 1) * limit

        domain = [('employee_id', '=', employee.id)]
        Leave = request.env['hr.leave'].sudo()
        total = Leave.search_count(domain)
        leaves = Leave.search(domain, order='request_date_from desc', limit=limit, offset=offset)

        # build pager dict
        page_count = int(math.ceil(float(total) / limit)) if total else 1

        def _get_url(p):
            return "%s?page=%s" % ("/my/timeoff", p) if p > 1 else "/my/timeoff"

        pager = {
            'page_count': page_count,
            'offset': offset,
            'page': {'url': _get_url(page), 'num': page},
            'page_first': {'url': _get_url(1), 'num': 1},
            'page_previous': {'url': _get_url(max(1, page - 1)), 'num': max(1, page - 1)},
            'page_next': {'url': _get_url(page + 1 if page + 1 <= page_count else page_count), 'num': page + 1 if page + 1 <= page_count else page_count},
            'page_last': {'url': _get_url(page_count), 'num': page_count},
            'pages': [{'url': _get_url(p), 'num': p} for p in range(1, page_count + 1)],
        }

        return request.render('portal_hr_eta.portal_my_timeoff', {
            'leaves': leaves,
            'attachments_count_map': {l.id: len(l.supported_attachment_ids) for l in leaves},
            'pager': pager,
            'page': page,
            'limit': limit,
            'total': total,
        })

    # =================================================
    # Time Off Details
    # =================================================
    @http.route('/my/timeoff/<int:leave_id>', type='http', auth='user', website=True)
    def portal_timeoff_details(self, leave_id):
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

        if not leave.exists() or leave.employee_id != employee:
            raise AccessError()

        # build form pager across this employee's leaves ordered by date desc
        Leave = request.env['hr.leave'].sudo()
        ids = Leave.search([('employee_id', '=', employee.id)], order='request_date_from desc').ids
        form_pager = None
        if leave.id in ids:
            idx = ids.index(leave.id)
            prev_id = ids[idx - 1] if idx > 0 else None
            next_id = ids[idx + 1] if idx < len(ids) - 1 else None
            form_pager = {
                'prev_url': f"/my/timeoff/{prev_id}" if prev_id else None,
                'next_url': f"/my/timeoff/{next_id}" if next_id else None,
                'index': idx + 1,
                'total': len(ids),
            }

        return request.render('portal_hr_eta.portal_timeoff_details', {
            'leave': leave,
            'attachments_count': len(leave.supported_attachment_ids),
            'form_pager': form_pager,
        })

    # =================================================
    # Create Time Off (Native Supporting Documents)
    # =================================================
    @http.route('/my/timeoff/new', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_timeoff_create(self, **post):
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        if not employee:
            raise AccessError()

        leave_types = request.env['hr.leave.type'].sudo().search([])

        if request.httprequest.method == 'POST':
            try:
                leave_type_id = int(post.get('leave_type', 0))
                if not leave_type_id:
                    raise ValueError("Invalid leave type")
            except (ValueError, TypeError):
                raise AccessError("Invalid leave type provided")

            files = request.httprequest.files.getlist('attachments')
            attachment_ids = []

            # ✅ Create attachments with error handling
            for f in files:
                try:
                    att = request.env['ir.attachment'].sudo().create({
                        'name': f.filename,
                        'datas': base64.b64encode(f.read()),
                        'res_model': 'hr.leave',
                        'mimetype': f.content_type,
                    })
                    attachment_ids.append(att.id)
                except Exception:
                    continue  # Skip failed uploads

            # ✅ Create leave with validation
            leave = request.env['hr.leave'].sudo().create({
                'name': post.get('description') or 'Time Off Request',
                'employee_id': employee.id,
                'holiday_status_id': leave_type_id,
                'request_date_from': post.get('date_from'),
                'request_date_to': post.get('date_to'),
                'supported_attachment_ids': [(6, 0, attachment_ids)],
            })

            # Link attachments to record
            if attachment_ids:
                request.env['ir.attachment'].sudo().browse(attachment_ids).write({
                    'res_id': leave.id
                })

            return request.redirect('/my/timeoff')

        return request.render('portal_hr_eta.portal_timeoff_create', {
            'leave_types': leave_types,
            'employee': employee,
        })

    # =================================================
    # Approvals List
    # =================================================
    @http.route('/my/timeoff/approvals', type='http', auth='user', website=True)
    def portal_timeoff_approvals(self, **kw):
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        if not employee:
            raise AccessError()

        is_hr_manager = request.env.user.has_group('hr.group_hr_manager')

        domain = [('state', 'in', ['confirm', 'validate1'])]
        if not is_hr_manager:
            domain.append(('employee_id.parent_id', '=', employee.id))

        # pagination
        try:
            page = int(kw.get('page', 1))
            if page < 1:
                page = 1
        except (TypeError, ValueError):
            page = 1
        # support optional page_size for testing: ?page_size=5
        try:
            page_size = int(kw.get('page_size')) if kw.get('page_size') else None
            if page_size and (page_size < 1 or page_size > 100):
                page_size = None
        except (TypeError, ValueError):
            page_size = None
        limit = page_size or 10
        offset = (page - 1) * limit

        Leave = request.env['hr.leave'].sudo()
        total = Leave.search_count(domain)
        approvals = Leave.search(domain, limit=limit, offset=offset)

        # build pager dict
        page_count = int(math.ceil(float(total) / limit)) if total else 1

        def _get_url(p):
            return "%s?page=%s" % ("/my/timeoff/approvals", p) if p > 1 else "/my/timeoff/approvals"

        pager = {
            'page_count': page_count,
            'offset': offset,
            'page': {'url': _get_url(page), 'num': page},
            'page_first': {'url': _get_url(1), 'num': 1},
            'page_previous': {'url': _get_url(max(1, page - 1)), 'num': max(1, page - 1)},
            'page_next': {'url': _get_url(page + 1 if page + 1 <= page_count else page_count), 'num': page + 1 if page + 1 <= page_count else page_count},
            'page_last': {'url': _get_url(page_count), 'num': page_count},
            'pages': [{'url': _get_url(p), 'num': p} for p in range(1, page_count + 1)],
        }

        return request.render('portal_hr_eta.portal_timeoff_approvals_list', {
            'approvals': approvals,
            'approvals_attachments_count_map': {a.id: len(a.supported_attachment_ids) for a in approvals},
            'pager': pager,
            'page': page,
            'limit': limit,
            'total': total,
        })

    # =================================================
    # Approval Details
    # =================================================
    @http.route('/my/timeoff/approvals/<int:leave_id>', type='http', auth='user', website=True)
    def portal_timeoff_approval_details(self, leave_id):
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

        is_hr_manager = request.env.user.has_group('hr.group_hr_manager')
        is_manager = leave.employee_id.parent_id == employee

        if not leave.exists() or not (is_hr_manager or is_manager):
            raise AccessError()

        # build form pager across approvals (same domain used in list)
        domain = [('state', 'in', ['confirm', 'validate1'])]
        if not is_hr_manager:
            domain.append(('employee_id.parent_id', '=', employee.id))
        Leave = request.env['hr.leave'].sudo()
        ids = Leave.search(domain).ids
        form_pager = None
        if leave.id in ids:
            idx = ids.index(leave.id)
            prev_id = ids[idx - 1] if idx > 0 else None
            next_id = ids[idx + 1] if idx < len(ids) - 1 else None
            form_pager = {
                'prev_url': f"/my/timeoff/approvals/{prev_id}" if prev_id else None,
                'next_url': f"/my/timeoff/approvals/{next_id}" if next_id else None,
                'index': idx + 1,
                'total': len(ids),
            }

        return request.render('portal_hr_eta.portal_timeoff_approval_details', {
            'leave': leave,
            'attachments_count': len(leave.supported_attachment_ids),
            'form_pager': form_pager,
        })

    # =================================================
    # Approve / Refuse
    # =================================================
    @http.route('/my/timeoff/approve/<int:leave_id>', type='http', auth='user', website=True)
    def portal_timeoff_approve(self, leave_id):
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

        is_hr_manager = request.env.user.has_group('hr.group_hr_manager')
        is_manager = leave.employee_id.parent_id == employee

        if not leave.exists() or not (is_hr_manager or is_manager):
            raise AccessError()

        leave.action_validate()
        return request.redirect('/my/timeoff/approvals')

    @http.route('/my/timeoff/refuse/<int:leave_id>', type='http', auth='user', website=True)
    def portal_timeoff_refuse(self, leave_id):
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

        is_hr_manager = request.env.user.has_group('hr.group_hr_manager')
        is_manager = leave.employee_id.parent_id == employee

        if not leave.exists() or not (is_hr_manager or is_manager):
            raise AccessError()

        leave.action_refuse()
        return request.redirect('/my/timeoff/approvals')

    # =================================================
    # Delete Time Off Request
    # =================================================
    @http.route('/my/timeoff/delete/<int:leave_id>', type='http', auth='user', website=True)
    def portal_timeoff_delete(self, leave_id):
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

        if not leave.exists() or leave.employee_id != employee:
            raise AccessError()

        # Only allow delete in draft state
        if leave.state != 'draft':
            raise AccessError()

        leave.unlink()
        return request.redirect('/my/timeoff')

    # =================================================
    # Delete Approval Request (Manager/HR only)
    # =================================================
    @http.route('/my/timeoff/approvals/delete/<int:leave_id>', type='http', auth='user', website=True)
    def portal_timeoff_approval_delete(self, leave_id):
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

        is_hr_manager = request.env.user.has_group('hr.group_hr_manager')
        is_manager = leave.employee_id.parent_id == employee

        if not leave.exists() or not (is_hr_manager or is_manager):
            raise AccessError()

        # Only allow delete in draft/confirm state
        if leave.state not in ('draft', 'confirm'):
            raise AccessError()

        leave.unlink()
        return request.redirect('/my/timeoff/approvals')
    @http.route('/my/timeoff/attachment/delete/<int:attachment_id>', type='http', auth='user', website=True)
    def portal_timeoff_delete_attachment(self, attachment_id):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)

        if not attachment.exists() or attachment.res_model != 'hr.leave':
            raise AccessError()

        leave = request.env['hr.leave'].sudo().browse(attachment.res_id)

        # ❌ Block delete after approval (native behavior)
        if leave.state in ('validate', 'refuse'):
            raise AccessError()

        attachment.unlink()
        return request.redirect(request.httprequest.referrer or '/my/timeoff')
