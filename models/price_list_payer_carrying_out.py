from odoo import models, fields, api
from .base_model import AmanatBaseModel

class PriceListPayerCarryingOut(models.Model, AmanatBaseModel):
    _name = 'amanat.price_list_payer_carrying_out'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Прайс лист: Плательщик-Исполнение'

    name = fields.Char(string="Наименования", tracking=True)
    payer_partner = fields.Many2one('amanat.payer', string="Плательщик субагенты", tracking=True)
    counterparties = fields.Many2one('amanat.contragent', string="Контрагенты", tracking=True)
    date_start = fields.Date(string="Дата начало", tracking=True)
    date_end = fields.Date(string="Дата конец", tracking=True)
    today_date = fields.Date(string="Даты TODAY", default=fields.Date.context_today, tracking=True)
    period_days = fields.Integer(string="Период дней", compute="_compute_period_days", store=True)
    accrual_percentage = fields.Float(string="Начисления", tracking=True)
    fixed_deal_fee = fields.Float(string="Фикс за сделку в $", tracking=True)
    min_application_amount = fields.Float(string="Минимальная сумма заявки", tracking=True)
    max_application_amount = fields.Float(string="Максимальная сумма заявки", tracking=True)
    bind_field = fields.Boolean(string="Привязать", tracking=True)
    applications = fields.One2many('amanat.applications', 'price_list_payer_carrying_out_id', string="Заявки")

    @api.depends('date_start', 'date_end')
    def _compute_period_days(self):
        for record in self:
            if record.date_start and record.date_end:
                record.period_days = (record.date_end - record.date_start).days
            else:
                record.period_days = 0
