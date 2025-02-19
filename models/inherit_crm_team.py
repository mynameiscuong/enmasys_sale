# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class InheritCrmTeam(models.Model):
    _inherit = 'crm.team'

    x_sale_manager_id = fields.Many2one('res.users', string='Quản lý')
