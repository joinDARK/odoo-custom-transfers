# models/price_list_partners.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Price_list_partners(models.Model, AmanatBaseModel):
    _name = 'amanat.price_list_partners'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Прайс лист партнеры'

    name = fields.Char(string="Наименование")
    payer_partner = fields.Many2one('amanat.payer', string="Партнеры плательщики")
    contragents_ids = fields.Many2many(
        'amanat.contragent',
        related='payer_partner.contragents_ids',
        string='Контрагенты партнёра',
        readonly=True,
        store=False,
    )
    accrual_type = fields.Selection(
        [
            ('inv_sum_hidden_rate', '1 Уровень Сумма инвойса + Скрытый курс'),
            ('inv_sum_foreign_currency', '1 Уровень Сумма инвойса в ин. валюте'),
            ('profit_level', '2 Уровень Прибыль'),
        ],
        string='Тип начисления',
        tracking=True
    )
    date_start = fields.Date(string="Дата начало")
    date_end = fields.Date(string="Дата конец")
    today_date = fields.Date(string="TODAY", default=fields.Date.context_today)
    period_days = fields.Integer(string="Период дней", compute="_compute_period_days", store=True, readonly=False, tracking=True)
    currency_type = fields.Selection(
        [
            ('foreign_currency', 'Ин валюта'),
            ('rub', 'RUB'),
        ],
        string="Тип валюты",
        tracking=True
    )
    type_binding = fields.Selection([
        ('auto', 'Авто'),
        ('manual', 'Ручками')
    ], string="Тип подвязки")
    accrual_percentage = fields.Float(string="% Начисления")
    fixed_deal_fee = fields.Float(string="Фикс за сделку $")
    min_application_amount = fields.Float(string="Минимальная сумма заявки $")
    bind_field = fields.Boolean(string="Привязать")

    zayavka_ids = fields.One2many(
        'amanat.zayavka',
        'price_list_partners_id',
        string='Заявки'
    )
    zayavka_ids_2 = fields.One2many(
        'amanat.zayavka',
        'price_list_partners_id_2',
        string='Заявки copy'
    )
    zayavka_ids_3 = fields.One2many(
        'amanat.zayavka',
        'price_list_partners_id_3',
        string='Заявки copy copy'
    )
    zayavka_ids_4 = fields.One2many(
        'amanat.zayavka',
        'price_list_partners_id_4',
        string='Заявки copy copy copy'
    )
    zayavka_ids_5 = fields.One2many(
        'amanat.zayavka',
        'price_list_partners_id_5',
        string='Заявки copy copy copy copy'
    )
    max_application_amount = fields.Float(string="Максимальная сумма заявки $")

    @api.depends('date_start', 'date_end')
    def _compute_period_days(self):
        for record in self:
            if record.date_start and record.date_end:
                record.period_days = (record.date_end - record.date_start).days
            else:
                record.period_days = 0