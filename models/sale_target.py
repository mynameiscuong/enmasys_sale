from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta, date, time


class SaleTarget(models.Model):
    _name = 'sale.target'
    _description = 'Mục tiêu doanh số'

    business_plan_id = fields.Many2one('business.plan', string='Kế hoạch kinh doanh')
    # import_id = fields.Many2one('sale.target.import', 'Import ID')
    day = fields.Date(string='Day')
    wday = fields.Selection([('0', 'Thứ Hai'),
                             ('1', 'Thứ Ba'),
                             ('2', 'Thứ Tư'),
                             ('3', 'Thứ Năm'),
                             ('4', 'Thứ Sáu'),
                             ('5', 'Thứ Bảy'),
                             ('6', 'Chủ Nhật')], string='Days of Week', compute='_compute_wday', store=True)
    partner_group_id = fields.Many2one('res.partner.group', string='Customer group', compute='_compute_partner_group_id', store=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    user_id = fields.Many2one('res.users', string='Employees', compute='_compute_user_id', store=True)
    target_revenue = fields.Float(string='Target')
    actual_revenue = fields.Float(string='Actual', compute='_compute_actual_revenue', store=True)
    year = fields.Integer(related='business_plan_id.year', store=True)
    rate_achieved = fields.Float(string="Rate Achieved", compute='_compute_rate_achieved', store=True)
    store_id = fields.Many2one('hr.department', 'Store')
    date_from = fields.Date(string='From date')
    date_to = fields.Date(string='To date')

    month = fields.Selection([
        ('1', 'Jan'),
        ('2', 'Feb'),
        ('3', 'Mar'),
        ('4', 'Apr'),
        ('5', 'May'),
        ('6', 'Jun'),
        ('7', 'Jul'),
        ('8', 'Aug'),
        ('9', 'Sep'),
        ('10', 'Oct'),
        ('11', 'Nov'),
        ('12', 'Dec'),
    ], string='Month')

    @api.onchange('month')
    def onchange_month(self):
        if self.month and self.year:
            month = int(self.month)
            year = self.year
            first_day = datetime(year, month, 1)
            # Cập nhật để xử lý tháng 12
            last_day = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year + 1, 1, 1) - timedelta(days=1)
            self.date_from = first_day
            self.date_to = last_day

    @api.depends('partner_id')
    def _compute_partner_group_id(self):
        for record in self:
            if record.partner_id:
                record.partner_group_id = record.partner_id.partner_group_id
            else:
                record.partner_id = None

    @api.depends('partner_id')
    def _compute_user_id(self):
        for record in self:
            if record.partner_id:
                record.user_id = record.partner_id.user_id
            else:
                record.user_id = None

    @api.depends('day', 'partner_id', 'business_plan_id.status', 'month')
    def _compute_actual_revenue(self):
        for record in self:
            if record.day:
                if record.business_plan_id.status == 'confirm':
                    domain = [('invoice_date', '>=', datetime.combine(record.day, time.min)),
                              ('invoice_date', '<=', datetime.combine(record.day, time.max)), ('state', '=', 'posted')]
                    if record.partner_id:
                        domain.append(('partner_id', '=', record.partner_id.id))
                    domain_invoice = domain + [('move_type', '=', 'out_invoice')]
                    domain_refund = domain + [('move_type', '=', 'out_refund')]
                    invoice_total = sum(self.env['account.move'].search(domain_invoice).mapped('amount_untaxed'))
                    refund_total = sum(self.env['account.move'].search(domain_refund).mapped('amount_untaxed'))
                    record.actual_revenue = invoice_total - refund_total

                elif record.month and record.year:
                    if record.business_plan_id.status == 'confirm':
                        current_date = record.date_from
                        actual_revenue = 0
                        while current_date <= record.date_to:
                            if record.business_plan_id.status == 'confirm':
                                domain = [('invoice_date', '>=', datetime.combine(current_date, time.min)),
                                          ('invoice_date', '<=', datetime.combine(current_date, time.max)), ('state', '=', 'posted')]
                                if record.partner_id:
                                    domain.append(('partner_id', '=', record.partner_id.id))
                                domain_invoice = domain + [('move_type', '=', 'out_invoice')]
                                domain_refund = domain + [('move_type', '=', 'out_refund')]
                                invoice_total = sum(self.env['account.move'].search(domain_invoice).mapped('amount_untaxed'))
                                refund_total = sum(self.env['account.move'].search(domain_refund).mapped('amount_untaxed'))
                                actual_revenue += invoice_total - refund_total
                            current_date += timedelta(days=1)
                        record.actual_revenue = actual_revenue
                else:
                    record.actual_revenue = 0
            else:
                record.actual_revenue = 0

    @api.constrains('day', 'year')
    def _constrains_day(self):
        for record in self:
            if record.day and record.year:
                if record.day.year != record.business_plan_id.year:
                    raise UserError(_("Phải chọn ngày trong năm %s" % record.business_plan_id.year))

    @api.constrains('day', 'partner_id', 'user_id')
    def _constrains_sale_target(self):
        for record in self:
            if record.day:
                sale_targets = self.search(
                    [('business_plan_id', '=', record.business_plan_id.id), ('day', '=', record.day), ('id', '!=', record.id)])
                if len(sale_targets) > 0:
                    msg = 'Không cho phép trùng ngày kế hoạch mà có dữ liệu trống: Ngày %s' % record.day
                    if not record.partner_id:
                        raise UserError(_(msg))
                    if not record.user_id:
                        raise UserError(_(msg))
                    if (len(sale_targets.mapped('partner_id.id')) == 0 or record.partner_id.id in sale_targets.mapped(
                            'partner_id.id')) and (
                            len(sale_targets.mapped('user_id.id')) == 0 or record.user_id.id in sale_targets.mapped('user_id.id')):
                        raise UserError(_(msg))

    @api.depends('target_revenue', 'actual_revenue')
    def _compute_rate_achieved(self):
        for record in self:
            record.rate_achieved = record.actual_revenue / record.target_revenue if record.target_revenue != 0 else 0
