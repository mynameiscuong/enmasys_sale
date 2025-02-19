import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CommissionPerformanceDataReport(models.TransientModel):
    _name = "commission.performance.data.report"
    _description = "Performance-Based Compensation (Commission) Calculation Sheet for Salespersons and Architects"

    # inverse_name
    x_report_id = fields.Many2one(
        comodel_name="commission.performance.report", ondelete="cascade",
        string="Performance-Based Compensation (Commission) Calculation Sheet for Salespersons and Architects")

    # data
    x_order_sequence = fields.Integer(string="Order Sequence")
    x_architect_id = fields.Many2one(comodel_name="res.partner", string="Architect")
    x_sale_person_id = fields.Many2one(comodel_name="res.users", string="Sale-Person")
    x_sale_resource_name = fields.Char(string="Sale-Resource")
    x_department_id = fields.Many2one(comodel_name="hr.department", string="Department",)
    x_order_total_amount = fields.Float(string="Total amount")
    x_commission_amount = fields.Float(string="Commission amount")
    x_currency_id = fields.Many2one(
        comodel_name="res.currency", string="Currency", default=lambda self: self.env.company.currency_id.id)
    x_note = fields.Text(string="Note")

