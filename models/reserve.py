# models/reserve.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Reserve(models.Model, AmanatBaseModel):
    _name = 'amanat.reserve'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Валютный резерв 1'

    subagent_payer = fields.Char(string="Плательщик субагента")
    counterparties = fields.Many2one('amanat.contragent', string="Контрагенты (из Плательщика субагента)")
    date_start = fields.Date(string="Дата начала")
    date_end = fields.Date(string="Дата конец")
    period_days = fields.Integer(string="Период дней", compute="_compute_period_days", store=True)
    today_date = fields.Date(string="Даты TODAY", default=fields.Date.context_today)
    accrual_percentage = fields.Float(string="% Начисления")
    fixed_deal_fee = fields.Float(string="Фикс за сделку $")
    min_application_amount = fields.Float(string="Минимальная сумма заявки $")
    max_application_amount = fields.Float(string="Максимальная сумма заявки $")
    bind_field = fields.Boolean(string="Привязать")
    applications = fields.Many2one('amanat.zayavka', string="Заявки")

    @api.depends('date_start', 'date_end')
    def _compute_period_days(self):
        for record in self:
            if record.date_start and record.date_end:
                record.period_days = (record.date_end - record.date_start).days
            else:
                record.period_days = 0