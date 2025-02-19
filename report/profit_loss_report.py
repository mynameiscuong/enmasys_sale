from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, time

class ProfitLossReport(models.TransientModel):
    _name = 'profit.loss.report'
    _rec_name = 'dis_name'
    _description = 'Báo cáo lãi lỗ'

    dis_name = fields.Char(string='Tên hiển thị', default='Báo cáo lãi lỗ')
    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    product_category_ids = fields.Many2many('product.category', 'profit_loss_report_product_category_rel', string='Nhóm sản phẩm')
    product_ids = fields.Many2many('product.product', 'profit_loss_report_product_rel', string='Sản phẩm (Biến thể sản phẩm)', domain="[('categ_id', 'in', product_category_ids)]")
    profit_loss_report_line_ids = fields.One2many('profit.loss.report.line', 'profit_loss_report_id')

    @api.constrains('date_from', 'date_to')
    def _constraint_date(self):
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError(_("Từ ngày không thể lớn hơn đến ngày!"))
                

    def action_cal(self):
        domain = [('order_id.state', 'in', ['sale', 'done']), ('order_id.x_type_order', 'in', ['sale', 'allocation'])]
        if self.date_from and not self.date_to:
            domain.extend([('order_id.date_order', '>=', datetime.combine(self.date_from, time.min)), ('order_id.date_order', '<=', datetime.combine(datetime.now(), time.max))])
        elif not self.date_from and self.date_to:
            domain.append(('order_id.date_order', '<=', datetime.combine(self.date_to, time.max)))
        elif self.date_from and self.date_to:
            domain.extend([('order_id.date_order', '>=', datetime.combine(self.date_from, time.min)), ('order_id.date_order', '<=', datetime.combine(self.date_to, time.max))])
        if self.product_category_ids:
            domain.append(('product_id.categ_id', 'in', self.product_category_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        order_lines = self.env['sale.order.line'].search(domain)
        values = [(5, 0, 0)]
        products = order_lines.mapped('product_id')
        for product in products:
            qty = 0
            price = 0
            for line in order_lines:
                if product.id == line.product_id.id:
                    qty += line.product_uom_qty
                    price += line.price_subtotal
                
            values.append((0, 0, {
                'product_id': product.id,
                'qty': qty,
                'uom_qty_id': product.uom_id.id,
                'min_price': product.standard_price * qty,
                'price': price,
                'profit_loss': price - (product.standard_price * qty),
                'profit_loss_percentage': (price - (product.standard_price * qty)) / price if price != 0 else 0
            }))
        self.write({'profit_loss_report_line_ids': values})

class ProfitLossReportLine(models.TransientModel):
    _name = 'profit.loss.report.line'
    _description = 'Chi tiết báo cáo lãi lỗ'

    profit_loss_report_id = fields.Many2one('profit.loss.report')
    product_id = fields.Many2one('product.product', string='Sản phẩm (Biến thể)')
    qty = fields.Float(string='Số lượng')
    uom_qty_id = fields.Many2one('uom.uom', string='Đơn vị')
    min_price = fields.Float(string='Doanh thu theo giá min')
    price = fields.Float(string='Doanh thu')
    profit_loss = fields.Float(string='Lãi/lỗ')
    profit_loss_percentage = fields.Float(string='Lãi/lỗ (%)')