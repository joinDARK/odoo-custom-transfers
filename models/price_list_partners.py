# models/price_list_partners.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Price_list_partners(models.Model, AmanatBaseModel):
    _name = 'amanat.price_list_partners'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Прайс лист партнеры'

    name = fields.Char(string="Наименование")
    payer_partner = fields.Many2one('amanat.payer', string="Партнеры плательщики")
    counterparties = fields.Many2one('amanat.contragent', string="Контрагенты")
    date_start = fields.Date(string="Дата начало")
    date_end = fields.Date(string="Дата конец")
    today_date = fields.Date(string="TODAY", default=fields.Date.context_today)
    period_days = fields.Integer(string="Период дней", compute="_compute_period_days", store=True)
    type_binding = fields.Selection([
        ('auto', 'Авто'),
        ('manual', 'Ручками')
    ], string="Тип подвязки")
    accrual_percentage = fields.Float(string="% Начисления")
    fixed_deal_fee = fields.Float(string="Фикс за сделку $")
    min_application_amount = fields.Float(string="Минимальная сумма заявки $")
    bind_field = fields.Boolean(string="Привязать")

    @api.depends('date_start', 'date_end')
    def _compute_period_days(self):
        for record in self:
            if record.date_start and record.date_end:
                record.period_days = (record.date_end - record.date_start).days
            else:
                record.period_days = 0