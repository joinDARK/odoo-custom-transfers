from odoo import models, fields

class MoneyCostRule(models.Model):
    _name = 'amanat.money_cost_rule'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Правило Себестоимость денег'

    name = fields.Char(string="Правило себестоимость денег", required=True, tracking=True)
    credit_rate = fields.Float(string="Ставка по кредиту", tracking=True)
    credit_period = fields.Integer(string="Кредитный период", tracking=True)
    extra_days = fields.Integer(string="Колво доп дней", tracking=True)
    zayavka_ids = fields.One2many(
        'amanat.zayavka',
        'money_cost_rule_id',
        string='Заявки'
    )
    date_start = fields.Date(string="Дата начало", tracking=True)
    date_end = fields.Date(string="Дата конец", tracking=True)

    min_application_amount = fields.Float(string="Минимальная сумма заявки $", tracking=True)
    max_application_amount = fields.Float(string="Максимальная сумма заявки $", tracking=True)

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