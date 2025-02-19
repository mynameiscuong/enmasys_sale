from odoo import models, fields, api

class CustomerHistory(models.Model):
    _name = 'customer.history'
    _description = 'Lịch sử khách hàng'

    customer_id = fields.Many2one('res.partner', string="Khách hàng", required=True)
    date = fields.Datetime(string="Ngày", default=fields.Datetime.now)
    responsible_employee_id = fields.Many2one('hr.employee', string="Nhân viên phụ trách")
    interested_products_ids = fields.Many2many('product.product', string="Sản phẩm quan tâm")
    request_types_ids = fields.Many2many('request.type', string="Loại yêu cầu")
    note = fields.Text(string="Mô tả")

    interested_products_display = fields.Char(compute="_compute_interested_products_display", string="Sản phẩm quan tâm")
    request_types_display = fields.Char(compute="_compute_request_types_display", string="Loại yêu cầu")

    @api.depends('interested_products_ids')
    def _compute_interested_products_display(self):
        for record in self:
            record.interested_products_display = ', '.join(record.interested_products_ids.mapped('name'))

    @api.depends('request_types_ids')
    def _compute_request_types_display(self):
        for record in self:
            record.request_types_display = ', '.join(record.request_types_ids.mapped('name'))
