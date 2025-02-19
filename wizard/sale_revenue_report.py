import base64

import xlsxwriter

from io import BytesIO
from datetime import datetime, timedelta

from odoo import models, fields, _
from odoo.exceptions import ValidationError, UserError


class SaleRevenueReport(models.TransientModel):
    _name = 'sale.revenue.report'
    _description = 'Sale Revenue Report'

    def domain_user_ids(self):
        try:
            domain = []
            if not self.env.user._is_system() and not self.env.user._is_admin():
                user_ids = self.get_list_user()
                domain = [('id', 'in', user_ids.ids)]

            return domain
        except Exception as e:
            raise ValidationError(e)

    name = fields.Char('Tên báo cáo', default='Báo cáo doanh thu')
    from_date = fields.Date('Từ ngày', default=fields.Datetime.today(), required=True)
    to_date = fields.Date('Đến ngày', default=fields.Datetime.today(), required=True)
    user_ids = fields.Many2many('res.users', string='Tên nhân viên', domain=domain_user_ids)
    partner_ids = fields.Many2many('res.partner', string='Khách hàng')
    product_ids = fields.Many2many('product.product', string='Sản phẩm')
    sale_ids = fields.Many2many('sale.order', string='Mã đơn hàng')

    line_ids = fields.One2many('sale.revenue.report.line', 'report_id', 'Chi tiết')
    detail_ids = fields.One2many('sale.revenue.report.detail', 'report_id', 'Chi tiết')

    partner_count = fields.Integer('Tổng khách hàng', default=0)
    total_previous_year_revenue = fields.Float('Tổng doanh thu năm trước', default=0)
    total_revenue_plan = fields.Float('Tổng kế hoạch ngày', default=0)
    total_price_subtotal = fields.Float('Tổng doanh thu trước thuế', default=0)
    total_last_year_percent = fields.Float('Tổng so với năm trước', default=0)
    total_day_percent = fields.Float('Tổng tỷ lệ đạt được', default=0)

    analytic_account_ids = fields.Many2many('account.analytic.account', string='Tài khoản phân tích')

    def action_generate(self):
        try:
            self.ensure_one()
            self.detail_ids = None
            self.line_ids = None

            if self.from_date == self.to_date:
                name = 'Báo cáo doanh thu ngày ' + self.from_date.strftime('%d/%m/%Y')
            else:
                name = 'Báo cáo doanh thu từ ngày %s đến ngày %s' % (self.from_date.strftime('%d/%m/%Y'), self.to_date.strftime('%d/%m/%Y'))
            self.name = name
            query = self._get_query_detail()
            self.env.cr.execute(query)
            query_2 = self._get_query_line()
            self.env.cr.execute(query_2)
            data_lines = self.env.cr.dictfetchall()
            self.env.cr.commit()
            total_previous_year_revenue = 0
            total_revenue_plan = 0
            total_price_subtotal = 0
            partner_count = 0
            line_vals = []
            partner = []
            for data in data_lines:
                analytic_name = self.convert_analytic_name(data.get('analytic_name'))
                partner_id = data.get('partner_id')
                revenue_plan = data.get('revenue_plan')
                price_subtotal = data.get('price_subtotal')
                previous_year_revenue = data.get('previous_year_revenue')
                vals = {
                    'user_id': data.get('user_id'),
                    'partner_id': partner_id,
                    'analytic_name': analytic_name,
                    'revenue_plan': revenue_plan,
                    'price_subtotal': price_subtotal,
                    'previous_year_revenue': previous_year_revenue,
                    'last_year_percent': data.get('last_year_percent'),
                    'day_percent': data.get('day_percent'),
                }
                total_revenue_plan += revenue_plan
                total_price_subtotal += price_subtotal
                total_previous_year_revenue += previous_year_revenue
                if partner_id not in partner:
                    partner_count += 1

                line_vals.append((0, 0, vals))

            self.line_ids = line_vals
            self.partner_count = partner_count
            self.total_previous_year_revenue = total_previous_year_revenue
            self.total_revenue_plan = total_revenue_plan
            self.total_price_subtotal = total_price_subtotal
            self.total_last_year_percent = round(total_price_subtotal / total_previous_year_revenue,
                                                 4) if total_previous_year_revenue else 1
            self.total_day_percent = round(total_price_subtotal / total_revenue_plan, 4) if total_revenue_plan else 1

        except Exception as e:
            raise ValidationError(e)

    def print_report_xlsx(self):
        try:
            self.ensure_one()
            action = self.env['ir.actions.report'].search([
                ('model', '=', self._name),
                ('report_name', '=', 'enmasys_sale.sale_revenue_xlsx'),
                ('report_type', '=', 'xlsx'),
            ], limit=1)
            if not action:
                raise UserError(_('Report Template not found'))
            context = dict(self.env.context)
            return action.with_context(context).report_action(self)
        except Exception as e:
            raise ValidationError(e)

    def _cron_auto_send_mail(self):
        try:
            user_ids = self.get_all_sale_user()
            if not user_ids:
                return

            today = datetime.now() + timedelta(hours=7) - timedelta(days=1)
            today = today.date()
            self.action_delete_attachment_previous()
            for user in user_ids:
                # lấy danh sách sale team đang quản lý
                list_users = self.get_list_user(user)
                report_id = self.env['sale.revenue.report'].create({
                    'from_date': today,
                    'to_date': today,
                    'user_ids': [(6, 0, list_users.ids)],
                })
                report_id.action_send_mail(user.partner_id.email)
        except Exception as e:
            raise ValidationError(e)

    def action_send_mail(self, email_to):
        try:
            self.ensure_one()
            if not email_to:
                return
            template = self.env.ref('enmasys_sale.sale_revenue_report_mail_template')
            self.action_generate()
            attachment_id = self.action_create_attachment_report()
            lang = self.env.context.get('lang')
            ctx = {
                'email_to': email_to,
                'default_lang': lang,
            }
            template.attachment_ids = [(4, attachment_id.id)]
            template.with_context(ctx).send_mail(self.id, raise_exception=False, force_send=True)
            template.attachment_ids = [(5, 0, 0)]
            return

        except Exception as e:
            raise ValidationError(e)

    def action_delete_attachment_previous(self):
        try:
            attachment_ids = self.env['ir.attachment'].search(
                [('res_model', '=', 'mail.template'), ('res_name', '=', 'Gửi email báo cáo doanh thu'),
                 ('create_date', '<', datetime.now())])
            attachment_ids.unlink()
        except Exception as e:
            raise ValidationError(e)

    def get_all_sale_user(self):
        try:
            # list_users = self.env['res.users']
            # team_ids = self.env['crm.team'].search([])
            # list_users |= team_ids.mapped('x_sale_manager_id')
            # list_users |= team_ids.mapped('user_id')
            # list_users |= team_ids.mapped('member_ids')
            list_users = self.env.ref('enmasys_sale_revenue_report.group_receive_revenue_report').users
            return list_users
        except Exception as e:
            raise ValidationError(e)

    def get_list_user(self, user_id=False):
        try:
            list_users = self.env['res.users']
            if not user_id:
                user_id = self.env.user
            list_users |= user_id
            team_manager_ids = self.env['crm.team'].search([('x_sale_manager_id', '=', user_id.id)])
            if team_manager_ids:
                list_users |= team_manager_ids.mapped('x_sale_manager_id')
                list_users |= team_manager_ids.mapped('user_id')
                list_users |= team_manager_ids.mapped('member_ids')

            team_leader_ids = self.env['crm.team'].search([('user_id', '=', user_id.id)])
            if team_leader_ids:
                list_users |= team_leader_ids.mapped('user_id')
                list_users |= team_leader_ids.mapped('member_ids')

            return list_users
        except Exception as e:
            raise ValidationError(e)

    def action_create_attachment_report(self):
        try:
            output = BytesIO()
            file_name = self.name + '.xlsx'
            workbook = xlsxwriter.Workbook(output)
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

            sheet = workbook.add_worksheet(self.name)

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
            for line in self.detail_ids:
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
            for line in self.line_ids:
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
            sheet_2.write('B' + str(row_count), self.partner_count, format_qty_int_total)
            sheet_2.write('D' + str(row_count), self.total_previous_year_revenue, format_qty_int_total)
            sheet_2.write('E' + str(row_count), self.total_revenue_plan, format_qty_int_total)
            sheet_2.write('F' + str(row_count), self.total_price_subtotal, format_qty_int_total)
            sheet_2.write('G' + str(row_count), self.total_last_year_percent * 100,
                          self.get_format_qty(self.total_last_year_percent * 100, format_qty_int_total, format_qty_float_total))
            sheet_2.write('H' + str(row_count), self.total_day_percent * 100,
                          self.get_format_qty(self.total_day_percent * 100, format_qty_int_total, format_qty_float_total))

            sheet_2.conditional_format(0, 0, row_count - 1, 7,
                                       {'type': 'no_blanks', 'format': border_format})
            sheet_2.conditional_format(0, 0, row_count - 1, 7,
                                       {'type': 'blanks', 'format': border_format})

            workbook.close()
            datas = base64.encodebytes(output.getvalue())
            attachment_data = {
                'name': file_name,
                'datas': datas,
                'res_model': self._name,
            }
            attachment_id = self.env['ir.attachment'].create(attachment_data)
            return attachment_id

        except Exception as e:
            raise ValidationError(e)

    def get_format_qty(self, qty, format_int, format_float):
        if qty % 1 == 0:
            format_qty = format_int
        else:
            format_qty = format_float
        return format_qty

    def _get_query_detail(self):
        try:
            if self.user_ids:
                user_ids = ','.join([str(idd) for idd in self.user_ids.ids])
            elif self.env.user._is_system() or self.env.user._is_admin():
                user_ids = '0'
            else:
                list_users = self.get_list_user()
                user_ids = ','.join([str(idd) for idd in list_users.ids]) if list_users else '-1'
            partner_ids = ','.join([str(idd) for idd in self.partner_ids.ids]) if self.partner_ids else '0'
            product_ids = ','.join([str(idd) for idd in self.product_ids.ids]) if self.product_ids else '0'
            sale_ids = ','.join([str(idd) for idd in self.sale_ids.ids]) if self.sale_ids else '0'
            analytic_account_ids = ','.join([str(idd) for idd in self.analytic_account_ids.ids]) if self.analytic_account_ids else '0'

            date_from = self.from_date.strftime('%d/%m/%Y')
            date_to = self.to_date.strftime('%d/%m/%Y')
            query = """
                insert into sale_revenue_report_detail(report_id, user_id, partner_id, sale_id, product_id,quantity, price_unit,
                        price_subtotal, margin_percent, analytic_account_id)
                select {report_id},
                       user_id,
                       partner_id,
                       order_id,
                       product_id,
                       sum(quantity),
                       abs(price_unit),
                       sum(price_subtotal) as price_subtotal,
                       case
                           --when price_unit < 0 then 0
                           when sum(quantity) != 0 and price_unit != 0 then
                               round(((sum(quantity) * (abs(price_unit))) / (sum(quantity) * price_unit))::numeric, 4)
                           else 0 end      as margin_percent,
                       analytic_account_id
                
                from (select rp.user_id              as user_id,
                             am.partner_id                   as partner_id,
                             sol.order_id                    as order_id,
                             aml.product_id                  as product_id,
                             case
                                 when am.move_type = 'out_refund' then - aml.quantity
                                 else aml.quantity end       as quantity,
                             case
                                 when am.move_type = 'out_refund' then - aml.price_unit
                                 else aml.price_unit end     as price_unit,
                             case
                                 when am.move_type = 'out_refund' then - aml.price_subtotal
                                 else aml.price_subtotal end as price_subtotal,
                             aal.account_id         as analytic_account_id
                      from account_move_line aml
                               join account_move am on aml.move_id = am.id
                               join res_partner rp on am.partner_id = rp.id
                               left join sale_order_line_invoice_rel solir on aml.id = solir.invoice_line_id
                               left join sale_order_line sol on solir.order_line_id = sol.id
                               left join account_analytic_line aal on aal.move_line_id = aml.id
                
                      where am.state = 'posted'
                        and am.move_type in ('out_invoice', 'out_refund', 'out_receipt')
                        and aml.display_type = 'product'
                        and aml.price_subtotal > 0
                        and (rp.user_id in ({user_ids}) or '0' = '{user_ids}')
                        and (am.partner_id in ({partner_ids}) or '0' = '{partner_ids}')
                        and (aal.account_id in ({analytic_account_ids}) or '0' = '{analytic_account_ids}')
                        and (aml.product_id in ({product_ids}) or '0' = '{product_ids}')
                        and (sol.order_id in ({sale_ids}) or '0' = '{sale_ids}')
                        and (am.invoice_date + interval '7 hours')::date >= to_date('{date_from}', 'dd/mm/yyyy')
                        and (am.invoice_date + interval '7 hours')::date <= to_date('{date_to}', 'dd/mm/yyyy')) as rv
                         join product_product pp on rv.product_id = pp.id
                         join product_template pt on pp.product_tmpl_id = pt.id
                group by user_id, partner_id, order_id, product_id, analytic_account_id, price_unit
                order by user_id, partner_id, order_id, product_id, analytic_account_id, price_unit


            """.format(report_id=self.id, user_ids=user_ids, partner_ids=partner_ids, product_ids=product_ids, sale_ids=sale_ids,
                       date_from=date_from, date_to=date_to, analytic_account_ids=analytic_account_ids)
            return query
        except Exception as e:
            raise ValidationError(e)

    def _get_query_line(self):
        try:
            if self.user_ids:
                user_ids = ','.join([str(idd) for idd in self.user_ids.ids])
            elif self.env.user._is_system() or self.env.user._is_admin():
                user_ids = '0'
            else:
                list_users = self.get_list_user()
                user_ids = ','.join([str(idd) for idd in list_users.ids]) if list_users else '-1'

            partner_ids = ','.join([str(idd) for idd in self.partner_ids.ids]) if self.partner_ids else '0'
            analytic_account_ids = ','.join([str(idd) for idd in self.analytic_account_ids.ids]) if self.analytic_account_ids else '0'

            date_from = self.from_date.strftime('%d/%m/%Y')
            date_to = self.to_date.strftime('%d/%m/%Y')
            year_difference_days = self.env['year.difference.days'].search(
                [('from_date', '<=', self.from_date), ('to_date', '>=', self.from_date), ('days', '!=', 0)], order='create_date desc',
                limit=1).days
            from_date = self.from_date.replace(year=self.from_date.year - 1) + timedelta(days=year_difference_days)
            to_date = self.to_date.replace(year=self.to_date.year - 1) + timedelta(days=year_difference_days)
            date_from_previous_year = from_date.strftime('%d/%m/%Y')
            date_to_previous_year = to_date.strftime('%d/%m/%Y')

            query = """
                select user_id,
                       partner_id,
                       string_agg(analytic_name || ' / ' || cast(price_subtotal as text), ',') as analytic_name,
                       sum(revenue_plan)                                                       as revenue_plan,
                       sum(price_subtotal)                                                     as price_subtotal,
                       sum(previous_year_revenue)                                              as previous_year_revenue,
                       sum(last_year_percent)                                                  as last_year_percent,
                       case
                           when sum(revenue_plan) != 0 then round((sum(price_subtotal) / sum(revenue_plan))::numeric, 4)
                           else 1 end                                                          as day_percent
                from (select user_id,
                             revenue.partner_id         as partner_id,
                             aaa.name->>'vi_VN'                   as analytic_name,
                             0                          as revenue_plan,
                             sum(price_subtotal)        as price_subtotal,
                             sum(previous_year_revenue) as previous_year_revenue,
                             case
                                 when sum(previous_year_revenue) != 0 then round(
                                         (sum(price_subtotal) / sum(previous_year_revenue))::numeric, 4)
                                 else 1 end             as last_year_percent
                      from (select rp.user_id                      as user_id,
                                   am.partner_id                   as partner_id,
                                   case
                                       when am.move_type = 'out_refund' then - aml.price_subtotal
                                       else aml.price_subtotal end as price_subtotal,
                                   0                               as previous_year_revenue,
                                   aal.account_id         as analytic_account_id
                            from account_move_line aml
                                     join account_move am on aml.move_id = am.id
                                     join res_partner rp on am.partner_id = rp.id
                                     left join sale_order_line_invoice_rel solir on aml.id = solir.invoice_line_id
                                     left join sale_order_line sol on solir.order_line_id = sol.id
                                     left join account_analytic_line aal on aal.move_line_id = aml.id
                
                            where am.state = 'posted'
                              and am.move_type in ('out_invoice', 'out_refund', 'out_receipt')
                              and aml.display_type = 'product'
                              and aml.price_subtotal != 0
                              and (rp.user_id in ({user_ids}) or '0' = '{user_ids}')
                              and (am.partner_id in ({partner_ids}) or '0' = '{partner_ids}')
                              and (aal.account_id in ({analytic_account_ids}) or '0' = '{analytic_account_ids}')
                              and (am.invoice_date + interval '7 hours')::date >= to_date('{date_from}', 'dd/mm/yyyy')
                              and (am.invoice_date + interval '7 hours')::date <= to_date('{date_to}', 'dd/mm/yyyy')
                
                            union all
                            -- kỳ trước
                            select rp.user_id                      as user_id,
                                   am.partner_id                   as partner_id,
                                   0                               as price_subtotal,
                                   case
                                       when am.move_type = 'out_refund' then - aml.price_subtotal
                                       else aml.price_subtotal end as previous_year_revenue,
                                   aal.account_id         as analytic_account_id
                            from account_move_line aml
                                     join account_move am on aml.move_id = am.id
                                     join res_partner rp on am.partner_id = rp.id
                                     left join sale_order_line_invoice_rel solir on aml.id = solir.invoice_line_id
                                     left join sale_order_line sol on solir.order_line_id = sol.id
                                     left join account_analytic_line aal on aal.move_line_id = aml.id
                
                            where am.state = 'posted'
                              and am.move_type in ('out_invoice', 'out_refund', 'out_receipt')
                              and aml.display_type = 'product'
                              and aml.price_subtotal > 0
                              and (rp.user_id in ({user_ids}) or '0' = '{user_ids}')
                              and (am.partner_id in ({partner_ids}) or '0' = '{partner_ids}')
                              and (aal.account_id in ({analytic_account_ids}) or '0' = '{analytic_account_ids}')
                              and (am.invoice_date + interval '7 hours')::date >= to_date('{date_from_previous_year}', 'dd/mm/yyyy')
                              and (am.invoice_date + interval '7 hours')::date <= to_date('{date_to_previous_year}', 'dd/mm/yyyy')) as revenue
                               left join account_analytic_account aaa on revenue.analytic_account_id = aaa.id
                      group by user_id, revenue.partner_id, analytic_account_id, aaa.name
                
                      union all
                
                      select st.user_id,
                             st.partner_id,
                             ''                     as analytic_name,
                             sum(st.target_revenue) as revenue_plan,
                             0                      as price_subtotal,
                             0                      as previous_year_revenue,
                             0                      as last_year_percent
                      from sale_target st
                               join business_plan bp on st.business_plan_id = bp.id
                      where bp.status = 'confirm'
                        and (st.user_id in ({user_ids}) or '0' = '{user_ids}')
                        and (st.partner_id in ({partner_ids}) or '0' = '{partner_ids}')
                        and st.day >= to_date('{date_from}', 'dd/mm/yyyy')
                        and st.day <= to_date('{date_to}', 'dd/mm/yyyy')
                      group by st.user_id, st.partner_id) rp
                group by user_id, partner_id
                order by user_id, partner_id

            """.format(report_id=self.id, user_ids=user_ids, partner_ids=partner_ids, date_from=date_from, date_to=date_to,
                       date_from_previous_year=date_from_previous_year, date_to_previous_year=date_to_previous_year,
                       analytic_account_ids=analytic_account_ids)
            return query
        except Exception as e:
            raise ValidationError(e)

    def convert_analytic_name(self, analytic_name):
        try:
            if not analytic_name:
                return ''
            list_analytic = analytic_name.split(',')
            for analytic in list_analytic:
                new_analytic = analytic.split('/')[0].strip()
                revenue = float(analytic.split('/')[1].strip())
                if revenue != 0:
                    revenue = '{:,.0f}'.format(revenue)
                    new_analytic = ' ' + new_analytic + ' / ' + revenue

                analytic_name = analytic_name.replace(analytic, new_analytic)

            return analytic_name.strip(', ')
        except Exception as e:
            raise ValidationError(e)


class SaleRevenueReportLine(models.TransientModel):
    _name = 'sale.revenue.report.line'
    _description = 'Sale Revenue Report Line'

    report_id = fields.Many2one('sale.revenue.report', 'Báo cáo')
    user_id = fields.Many2one('res.users', 'Tên nhân viên')
    partner_id = fields.Many2one('res.partner', 'Khách hàng')
    price_subtotal = fields.Float('Doanh thu trước thuế', default=0)
    previous_year_revenue = fields.Float('Doanh thu năm trước', default=0)
    revenue_plan = fields.Float('Kế hoạch ngày', default=0)
    last_year_percent = fields.Float('So với năm trước', default=0)
    day_percent = fields.Float('Tỷ lệ đạt được', default=0)

    analytic_account_id = fields.Many2one('account.analytic.account', 'Tài khoản phân tích')
    analytic_name = fields.Char('Tài khoản phân tích')


class SaleRevenueReportDetail(models.TransientModel):
    _name = 'sale.revenue.report.detail'
    _description = 'Sale Revenue Report Detail'

    report_id = fields.Many2one('sale.revenue.report', 'Báo cáo')
    user_id = fields.Many2one('res.users', 'Tên nhân viên')
    partner_id = fields.Many2one('res.partner', 'Khách hàng')
    sale_id = fields.Many2one('sale.order', 'Mã đơn hàng')
    product_id = fields.Many2one('product.product', 'Sản phẩm')
    quantity = fields.Float('Số lượng', default=0)
    price_unit = fields.Float('Đơn giá', default=0)
    price_subtotal = fields.Float('Doanh thu trước thuế', default=0)
    margin_percent = fields.Float('Biên lợi nhuận', default=0)

    analytic_account_id = fields.Many2one('account.analytic.account', 'Tài khoản phân tích')
