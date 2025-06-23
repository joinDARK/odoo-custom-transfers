from odoo import models, fields
from .base_model import AmanatBaseModel

class ExpenseRule(models.Model, AmanatBaseModel):
    _name = 'amanat.expense_rule'
    _description = 'Правило Расход на операционную деятельность'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Расход на операционную деятельность", required=True)
    percent = fields.Float(string="Процент", digits=(16, 4), tracking=True)
    zayavka_ids = fields.One2many(
        'amanat.zayavka',
        'expense_rule_id',
        string='Заявки'
    )
    date_start = fields.Date(string="Дата начала", tracking=True)
    date_end = fields.Date(string="Дата конца", tracking=True)