import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class InheritResPartner(models.Model):
    _inherit = "res.partner"

    x_commission = fields.Float(string="Commission", tracking=True)
