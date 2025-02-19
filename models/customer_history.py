from odoo import models, fields, api

class CustomerHistory(models.Model):
    _name = 'customer.history'
    _description = 'Lịch sử khách hàng'
    _rec_name = 'customer_id'

    customer_id = fields.Many2one('res.partner', string="Khách hàng", required=True)
    x_date = fields.Datetime(string="Ngày", default=fields.Datetime.now())
    x_responsible_employee_id = fields.Many2one('hr.employee', string="Nhân viên phụ trách")
    x_interested_products_ids = fields.Many2many('product.product','customer_history_id','product_id',string="Sản phẩm quan tâm")
    x_request_types_ids = fields.Many2many('request.type', string="Loại yêu cầu")
    x_note = fields.Text(string="Mô tả")
