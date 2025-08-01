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

    min_application_amount = fields.Float(string="Минимальная сумма заявки $", tracking=True)
    max_application_amount = fields.Float(string="Максимальная сумма заявки $", tracking=True)
    is_tezer_percent = fields.Boolean(string="Тезерный процент", tracking=True, default=False)

    min_percent_accrual = fields.Float(string="Мин %", tracking=True)
    max_percent_accrual = fields.Float(string="Макс %", tracking=True)
    contragent_zayavka_id = fields.Many2one(
        'amanat.contragent',
        string='Контрагент заявки',
        tracking=True
    )
    agent_zayavka_id = fields.Many2one(
        'amanat.contragent',
        string='Агент заявки',
        tracking=True
    )
    client_zayavka_id = fields.Many2one(
        'amanat.contragent',
        string='Клиент заявки',
        tracking=True
    )
    currency_zayavka = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'),
            ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
            ('usdt', 'USDT'),
            ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'),
            ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
            ('idr', 'IDR'), ('idr_cashe', 'IDR КЭШ'),
            ('inr', 'INR'), ('inr_cashe', 'INR КЭШ'),
        ],
        string='Валюта заявки',
        tracking=True
    )