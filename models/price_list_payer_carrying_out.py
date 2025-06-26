from odoo import models, fields, api
from .base_model import AmanatBaseModel

class PriceListPayerCarryingOut(models.Model, AmanatBaseModel):
    _name = 'amanat.price_list_payer_carrying_out'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Прайс лист Плательщика За проведение'

    name = fields.Char(string="Наименования", tracking=True)
    payer_partners = fields.Many2many(
        'amanat.payer',
        'amanat_price_list_payer_carrying_out_rel',  # имя таблицы-связи
        'price_list_id',  # поле-ссылка на эту модель
        'payer_id',       # поле-ссылка на модель плательщика
        string="Плательщики субагенты",
        tracking=True
    )
    contragent_ids = fields.Many2many(
        'amanat.contragent',
        string='Контрагенты',
        compute='_compute_contragent_ids',
        store=False,
        readonly=True
    )
    date_start = fields.Date(string="Дата начало", tracking=True)
    date_end = fields.Date(string="Дата конец", tracking=True)
    today_date = fields.Date(string="Даты TODAY", default=fields.Date.context_today, tracking=True)
    period_days = fields.Integer(string="Период дней", compute="_compute_period_days", store=True)
    accrual_percentage = fields.Float(string="% Начисления", tracking=True)
    fixed_deal_fee = fields.Float(string="Фикс за сделку в $", tracking=True)
    min_application_amount = fields.Float(string="Минимальная сумма заявки $", tracking=True)
    max_application_amount = fields.Float(string="Максимальная сумма заявки $", tracking=True)
    bind_field = fields.Boolean(string="Привязать", tracking=True)
    zayavka_ids = fields.One2many(
        'amanat.zayavka',               # модель заявок
        'price_list_carrying_out_id',   # имя поля Many2one в заявке
        string='Заявки'
    )

    @api.depends('date_start', 'date_end')
    def _compute_period_days(self):
        for record in self:
            if record.date_start and record.date_end:
                record.period_days = (record.date_end - record.date_start).days
            else:
                record.period_days = 0
    
    @api.depends('payer_partners')
    def _compute_contragent_ids(self):
        for rec in self:
            rec.contragent_ids = rec.payer_partners.mapped('contragents_ids')
