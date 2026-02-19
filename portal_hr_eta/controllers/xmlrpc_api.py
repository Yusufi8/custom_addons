# import xmlrpc.client
# import base64
#
# url = "http://localhost:8018"
# db = "odoo18"
# username = "admin"
# password = "admin"
#
# # 1️⃣ Authenticate
# common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
# uid = common.authenticate(db, username, password, {})
# print("UID:", uid)
#
# # 2️⃣ Object proxy
# models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
#
# # 3️⃣ CREATE employee
# emp_id = models.execute_kw(
#     db, uid, password,
#     'hr.employee', 'create',
#     [{
#         'name': 'Yusuf Khan',
#         'job_title': 'Integration Developer'
#     }]
# )
# print("Created employee:", emp_id)
#
# # 4️⃣ READ employee
# employee = models.execute_kw(
#     db, uid, password,
#     'hr.employee', 'read',
#     [[emp_id], ['name', 'job_title']]
# )
# print(employee)
#
# # 5️⃣ UPDATE image
# with open("photo.jpg", "rb") as img:
#     image_base64 = base64.b64encode(img.read()).decode()
#
# models.execute_kw(
#     db, uid, password,
#     'hr.employee', 'write',
#     [[emp_id], {'image_1920': image_base64}]
# )
#
# print("Image uploaded ✔")
#
#
#
#
# # from xmlrpc import client as xmlrpclib
# #
# # from odoo.api import model
# #
# # url = "http://localhost:8018"
# # username = "admin"
# # password = "9edb3538906968a027fecacf11e9cbc6e11dbe7c"
# # db = "odoo18"
# # full_url = "http://localhost:8018/xmlrpc/common"
# #
# # common = xmlrpclib.ServerProxy(url+"/xmlrpc/common")
# # uid = common.authenticate(db, username, password, {})
# # print(uid)
# #
# #
# #
# #
# # model = "res.partner"
# # search = []
# # method = "search"
# #
# # operation = xmlrpclib.ServerProxy(f"{url}/xmlrpc/2/object")
# # # list_of_partner_ids = operation.execute_kw(db, uid, password, model, method, [search])
# # # print("List of partner IDs:", list_of_partner_ids)
# # # print(len(list_of_partner_ids))
# # #
# # # method = "read"
# # # list_of_partner_ids = operation.execute(db, uid, password, model, method, list_of_partner_ids)
# # # print("List of partners", list_of_partner_ids)
# # #
# # # for employee in list_of_partner_ids:
# # #     print(employee['id'], employee['name'],employee['phone'], employee['email'])
# # #
# # # method = "search_count"
# # # list_of_partner_count = operation.execute(db, uid, password, model, method, search)
# # # print("Total partners count:", list_of_partner_count)
# # #
# # # method = "fields_get"
# # # fields_detaisl = operation.execute(db, uid, password, model, method, [])
# # # print(len(fields_detaisl))
# # #
# # # method = "search_read"
# # # partners = operation.execute_kw(db, uid, password, model, method, search)
# # # print("Partners via search_read:", partners)
# # #
# # # method = "create"
# # # new_partner = {
# # #     'name': 'New Partner from XML-RPC',
# # #     'company_type': 'person',
# # #     'phone': '1234567890',
# # #     'email': 'new@partner,com',
# # # }
# # # new_partner_id = operation.execute(db, uid, password, model, method, [new_partner])
# # # print("New partner created with ID:", new_partner_id)
# # #
# # # method = "write"
# # # is_to_write = operation.execute(db, uid, password, model, method, [134], {"phone": "9876543210"})
# # # print("Was the partner updated?", is_to_write)
# # #
# # # method = "unlink"
# # # is_deleted = operation.execute(db, uid, password, model, method, [134])
# # # print("Was the partner deleted?", is_deleted)