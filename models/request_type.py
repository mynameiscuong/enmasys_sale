from odoo import models, fields

class RequestType(models.Model):
    _name = 'request.type'
    _description = 'Loại Yêu Cầu'

    name = fields.Char(string="Tên loại yêu cầu", required=True)
    x_description = fields.Text(string="Mô tả")
