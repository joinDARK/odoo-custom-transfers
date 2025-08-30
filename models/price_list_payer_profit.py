from odoo import models, fields, api
from datetime import date

class PriceListPayerProfit(models.Model):
    _name = 'amanat.price_list_payer_profit'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Прайс лист Плательщика Прибыль'

    # Наименование — вводится пользователем (single line text)
    name = fields.Char(string='Наименование', tracking=True)

    # Плательщик субагента — связь one2many с моделью amanat.payer.
    # Предполагается, что в модели amanat.payer определено поле Many2one 'price_list_profit_id'
    payer_subagent_ids = fields.Many2many(
        'amanat.payer',
        'amanat_payer_pricelist_profit_rel',
        'pricelist_profit_id',
        'payer_id',
        string='Плательщик субагента',
        tracking=True
    )

    # Контрагенты — lookup из payer_subagent_ids по полю contragent_id.
    # Вычисляемое поле, собирающее контрагентов из связанных плательщиков.
    contragent_ids = fields.Many2many(
        'amanat.contragent',
        string='Контрагенты',
        compute='_compute_contragent_ids',
        store=False,
        readonly=True
    )

    # Субагенты — вычисляемое поле, собирающее субагентов из связанных плательщиков через контрагентов
    subagent_ids = fields.Many2many(
        'amanat.contragent',
        'amanat_price_list_profit_subagent_rel',
        'price_list_id',
        'subagent_id',
        string='Субагенты',
        compute='_compute_subagent_ids',
        store=True,
        readonly=True,
        tracking=True
    )

    # Дата начало и Дата конец
    date_start = fields.Date(string='Дата начало', tracking=True)
    date_end = fields.Date(string='Дата конец', tracking=True)

    # Период дней — вычисляется по разнице между датами.
    period_days = fields.Integer(
        string='Период дней',
        compute='_compute_period_days',
        readonly=False,
        store=True,
        tracking=True
    )

    # Даты TODAY — текущая дата в формате DD.MM.YYYY
    today_date_str = fields.Char(
        string='Даты TODAY',
        compute='_compute_today_date',
        store=False,
        tracking=True
    )

    # % Начисления (процент)
    percent_accrual = fields.Float(string='% Начисления', tracking=True)

    # Фикс за сделку $
    fixed_fee = fields.Float(string='Фикс за сделку $', tracking=True)

    # Минимальная и Максимальная сумма заявки $
    min_zayavka_amount = fields.Float(string='Минимальная сумма заявки $', tracking=True)
    max_zayavka_amount = fields.Float(string='Максимальная сумма заявки $', tracking=True, default=999999999)

    # Привязать — чекбокс, по умолчанию False
    is_bound = fields.Boolean(string='Привязать', default=False, tracking=True)

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

    # Заявки — связь one2many с моделью amanat.zayavka.
    # Предполагается, что в модели amanat.zayavka есть поле Many2one 'price_list_profit_id'
    zayavka_ids = fields.One2many(
        'amanat.zayavka',
        'price_list_profit_id',
        string='Заявки',
        tracking=True
    )

    @api.depends('payer_subagent_ids')
    def _compute_contragent_ids(self):
        for rec in self:
            rec.contragent_ids = rec.payer_subagent_ids.mapped('contragents_ids')

    @api.depends('payer_subagent_ids')
    def _compute_subagent_ids(self):
        """Вычисляет субагентов из связанных плательщиков через их контрагентов"""
        for rec in self:
            # Получаем всех контрагентов из плательщиков субагентов
            contragents = rec.payer_subagent_ids.mapped('contragents_ids')
            rec.subagent_ids = contragents

    @api.depends('date_start', 'date_end')
    def _compute_period_days(self):
        today = date.today()
        for rec in self:
            if rec.date_start:
                start = fields.Date.from_string(rec.date_start)
                if rec.date_end:
                    end = fields.Date.from_string(rec.date_end)
                else:
                    end = today
                rec.period_days = (end - start).days
            else:
                rec.period_days = 0

    @api.depends()
    def _compute_today_date(self):
        today_str = date.today().strftime("%d.%m.%Y")
        for rec in self:
            rec.today_date_str = today_str