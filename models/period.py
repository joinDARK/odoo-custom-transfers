from odoo import models, fields
from .base_model import AmanatBaseModel

class AmanatPeriod(models.Model, AmanatBaseModel):
    _name = 'amanat.period'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Период'

    name = fields.Char(string='Name', tracking=True)
    date_1 = fields.Date(string='Дата 1', tracking=True)
    date_2 = fields.Date(string='Дата 2', tracking=True)

    zayavka_ids = fields.Many2many('amanat.zayavka', string='Заявки', tracking=True)
