from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class YearDifferenceDays(models.Model):
    _name = 'year.difference.days'
    _description = 'Ngày chênh lệch năm'

    from_date = fields.Date('Từ ngày', required=True, index=True)
    to_date = fields.Date('Đến ngày', required=True, index=True)
    days = fields.Integer('Số ngày', default=0)

    @api.depends('from_date', 'to_date', 'days')
    def _compute_display_name(self):
        try:
            for rc in self:
                from_date = rc.from_date.strftime('%d/%m/%Y')
                to_date = rc.to_date.strftime('%d/%m/%Y')
                name = '{from_date} - {to_date} - {days}'.format(from_date=from_date, to_date=to_date, days=rc.days)
                rc.display_name = name

        except Exception as e:
            raise ValidationError(e)
