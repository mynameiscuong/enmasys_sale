from odoo import models, fields, _
from odoo.exceptions import ValidationError


class SaleRevenueReportXLSX(models.AbstractModel):
    _name = 'report.enmasys_sale.sale_revenue_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        try:
            for obj in lines:
                format_1 = workbook.add_format(
                    {'font_size': 12, 'valign': 'middle', 'bold': True, 'left': True, 'right': True, 'text_wrap': True,
                     })
                format_2 = workbook.add_format(
                    {'font_size': 12, 'valign': 'middle', 'bold': False, 'left': True, 'right': True, 'text_wrap': True,
                     })
                format_3 = workbook.add_format(
                    {'font_size': 12, 'valign': 'middle', 'bold': False, 'left': False, 'right': True, 'align': 'right',
                     'text_wrap': True})
                format_4 = workbook.add_format(
                    {'font_size': 12, 'valign': 'middle', 'bold': True, 'left': False, 'right': True, 'align': 'right',
                     'text_wrap': True})
                format_qty_float = workbook.add_format(
                    {'font_size': 12, 'valign': 'middle', 'bold': False, 'left': False, 'right': True, 'align': 'right',
                     'text_wrap': True, 'num_format': '#,##0.00'})
                format_qty_int = workbook.add_format(
                    {'font_size': 12, 'valign': 'middle', 'bold': False, 'left': False, 'right': True, 'align': 'right',
                     'text_wrap': True, 'num_format': '#,##0'})
                format_qty_float_total = workbook.add_format(
                    {'font_size': 12, 'valign': 'middle', 'bold': True, 'left': False, 'right': True, 'align': 'right',
                     'text_wrap': True, 'num_format': '#,##0.00'})
                format_qty_int_total = workbook.add_format(
                    {'font_size': 12, 'valign': 'middle', 'bold': True, 'left': False, 'right': True, 'align': 'right',
                     'text_wrap': True, 'num_format': '#,##0'})
                sheet = workbook.add_worksheet(obj.name)

                sheet.set_column(0, 0, 20)
                sheet.set_column(1, 1, 50)
                sheet.set_column(2, 2, 25)
                sheet.set_column(3, 3, 50)
                sheet.set_column(4, 4, 25)
                sheet.set_column(5, 9, 23)

                sheet.write('A1', 'Tên nhân viên', format_1)
                sheet.write('B1', 'Khách hàng', format_1)
                sheet.write('C1', 'Mã đơn hàng', format_1)
                sheet.write('D1', 'Tài khoản phân tích', format_1)
                sheet.write('E1', 'Mã sản phẩm', format_1)
                sheet.write('F1', 'Mã vạch', format_1)
                sheet.write('G1', 'Số lượng', format_1)
                sheet.write('H1', 'Giá bán', format_1)
                sheet.write('I1', 'Doanh thu trước thuế', format_1)
                sheet.write('J1', 'Biên lợi nhuận (%)', format_1)

                row_count = 2
                total_price_subtotal = 0
                total_quantity = 0
                for line in obj.detail_ids:
                    sheet.write('A' + str(row_count), line.user_id.name, format_2)
                    sheet.write('B' + str(row_count), line.partner_id.display_name, format_2)
                    sheet.write('C' + str(row_count), line.sale_id.name or '', format_2)
                    sheet.write('D' + str(row_count), line.analytic_account_id.display_name or '', format_2)
                    sheet.write('E' + str(row_count), line.product_id.name, format_2)
                    sheet.write('F' + str(row_count), line.product_id.barcode, format_2)
                    sheet.write('G' + str(row_count), line.quantity, self.get_format_qty(line.quantity, format_qty_int, format_qty_float))
                    sheet.write('H' + str(row_count), line.price_unit, format_qty_int)
                    sheet.write('I' + str(row_count), line.price_subtotal, format_qty_int)
                    sheet.write('J' + str(row_count), line.margin_percent * 100,
                                self.get_format_qty(line.margin_percent * 100, format_qty_int, format_qty_float))

                    total_price_subtotal += line.price_subtotal
                    total_quantity += line.quantity

                    row_count += 1

                sheet.write('F' + str(row_count), 'Tổng:  ', format_4)
                sheet.write('G' + str(row_count), total_quantity,
                            self.get_format_qty(total_quantity, format_qty_int_total, format_qty_float_total))
                sheet.write('I' + str(row_count), total_price_subtotal, format_qty_int_total)

                # tạo border cho bảng
                border_format = workbook.add_format({
                    'border': 1,
                    'align': 'left',
                    'font_size': 10
                })
                sheet.conditional_format(0, 0, row_count - 1, 9,
                                         {'type': 'no_blanks', 'format': border_format})
                sheet.conditional_format(0, 0, row_count - 1, 9,
                                         {'type': 'blanks', 'format': border_format})

                sheet_2 = workbook.add_worksheet('Tổng hợp')

                sheet_2.set_column(0, 0, 20)
                sheet_2.set_column(1, 2, 50)
                sheet_2.set_column(3, 4, 25)
                sheet_2.set_column(5, 7, 23)

                sheet_2.write('A1', 'Tên nhân viên', format_1)
                sheet_2.write('B1', 'Khách hàng', format_1)
                sheet_2.write('C1', 'Tài khoản phân tích', format_1)
                sheet_2.write('D1', 'Doanh thu năm trước', format_1)
                sheet_2.write('E1', 'Kế hoạch ngày', format_1)
                sheet_2.write('F1', 'Doanh thu trước thuế', format_1)
                sheet_2.write('G1', 'So với năm trước  (%)', format_1)
                sheet_2.write('H1', 'Tỷ lệ đạt được (%)', format_1)

                row_count = 2
                for line in obj.line_ids:
                    sheet_2.write('A' + str(row_count), line.user_id.name, format_2)
                    sheet_2.write('B' + str(row_count), line.partner_id.display_name, format_2)
                    sheet_2.write('C' + str(row_count), line.analytic_name or '', format_2)
                    sheet_2.write('D' + str(row_count), line.previous_year_revenue, format_qty_int)
                    sheet_2.write('E' + str(row_count), line.revenue_plan, format_qty_int)
                    sheet_2.write('F' + str(row_count), line.price_subtotal, format_qty_int)
                    sheet_2.write('G' + str(row_count), line.last_year_percent * 100,
                                  self.get_format_qty(line.last_year_percent * 100, format_qty_int, format_qty_float))
                    sheet_2.write('H' + str(row_count), line.day_percent * 100,
                                  self.get_format_qty(line.day_percent * 100, format_qty_int, format_qty_float))

                    row_count += 1

                sheet_2.write('C' + str(row_count), 'Tổng: ', format_4)
                sheet_2.write('B' + str(row_count), obj.partner_count, format_qty_int_total)
                sheet_2.write('D' + str(row_count), obj.total_previous_year_revenue, format_qty_int_total)
                sheet_2.write('E' + str(row_count), obj.total_revenue_plan, format_qty_int_total)
                sheet_2.write('F' + str(row_count), obj.total_price_subtotal, format_qty_int_total)
                sheet_2.write('G' + str(row_count), obj.total_last_year_percent * 100,
                              self.get_format_qty(obj.total_last_year_percent * 100, format_qty_int_total, format_qty_float_total))
                sheet_2.write('H' + str(row_count), obj.total_day_percent * 100,
                              self.get_format_qty(obj.total_day_percent * 100, format_qty_int_total, format_qty_float_total))

                sheet_2.conditional_format(0, 0, row_count - 1, 7,
                                           {'type': 'no_blanks', 'format': border_format})
                sheet_2.conditional_format(0, 0, row_count - 1, 7,
                                           {'type': 'blanks', 'format': border_format})


        except Exception as e:
            raise ValidationError(e)

    def get_format_qty(self, qty, format_int, format_float):
        if qty % 1 == 0:
            format_qty = format_int
        else:
            format_qty = format_float
        return format_qty
