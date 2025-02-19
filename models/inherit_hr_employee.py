import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class InheritHrEmployee(models.Model):
    _inherit = "hr.employee"

    x_commission = fields.Float(string="Commission", tracking=True)
