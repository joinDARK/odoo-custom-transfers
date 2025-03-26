# models/range.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Ranges(models.Model, AmanatBaseModel):
    _name = 'amanat.ranges'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Диапазон'

    range_id = fields.Char(string='ID Диапазона', required=True)
    date_start = fields.Date(string='Дата начало', tracking=True)
    date_end = fields.Date(string='Дата конец', tracking=True)
    date_start_copy = fields.Date(string='Дата начало copy', tracking=True) 
    data_end_copy = fields.Date(string='Дата конец copy', tracking=True) 
    compare_balance_date_1 = fields.Date(string='Сравнения баланса дата 1', tracking=True)
    compare_balance_date_2 = fields.Date(string='Сравнения баланса дата 2', tracking=True)
    reconciliation_date_1 = fields.Date(string='Сверка Дата 1', tracking=True)
    reconciliation_date_2 = fields.Date(string='Сверка Дата 2', tracking=True)