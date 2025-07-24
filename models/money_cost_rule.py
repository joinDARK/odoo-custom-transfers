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