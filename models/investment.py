from odoo import models, fields, api
from .base_model import AmanatBaseModel
from datetime import date, timedelta


class Investment(models.Model, AmanatBaseModel):
    _name = 'amanat.investment'
    _description = 'Инвестиции'
    _inherit = ['amanat.base.model', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='ID', 
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.investment.sequence'),
    )
    status = fields.Selection(
        [
            ('open', 'Открыта'),
            ('close', 'Закрыта'),
            ('archive', 'Архив')
        ],
        string='Статус',
        default='close',
        tracking=True
    )
    date = fields.Date(string='Дата', tracking=True, default=fields.Date.today)
    date_close = fields.Date(string='Дата закрытия', tracking=True)
    sender = fields.Many2one('amanat.contragent', string='Отправитель', tracking=True)
    payer_sender = fields.Many2one(
        'amanat.payer', 
        string='Плательщик отправитель', 
        tracking=True,
        domain="[('contragents_ids', 'in', sender)]"
    )
    receiver = fields.Many2one('amanat.contragent', string='Получатель', tracking=True)
    payer_receiver = fields.Many2one(
        'amanat.payer', 
        string='Плательщик получатель', 
        tracking=True,
        domain="[('contragents_ids', 'in', receiver)]"
    )
    percent = fields.Float(string='Процент', tracking=True)
    period = fields.Selection([
        ('calendar_day', 'Календарный день'),
        ('calendar_month', 'Календарный месяц'),
        ('calendar_year', 'Календарный год'),
        ('work_day', 'Рабочий день')
    ], string='Период', tracking=True)
    amount = fields.Float(string='Сумма', tracking=True)
    currency = fields.Selection([
        ('RUB', 'RUB'), ('USD', 'USD'), ('USDT', 'USDT'), ('AED', 'AED'),
        ('EURO', 'EURO'), ('CNY', 'CNY'), ('THB', 'THB'),
        ('THB_cash', 'THB КЭШ'), ('AED_cash', 'AED КЭШ'),
        ('EURO_cash', 'EURO КЭШ'), ('CNY_cash', 'CNY КЭШ'),
        ('USD_cash', 'USD КЭШ'), ('RUB_cash', 'RUB КЭШ')
    ], string='Валюта', tracking=True)
    fixed_amount = fields.Float(string='Фикс сумма', tracking=True)
    principal = fields.Float(
        string='Тело долга',
        compute='_compute_principal',
        store=True,
        tracking=True
    )
    calendar_days = fields.Integer(
        string='Календарных дней',
        compute='_compute_calendar_and_work_days',
        store=True,
        tracking=True
    )
    work_days = fields.Integer(
        string='Рабочих дней',
        compute='_compute_calendar_and_work_days',
        store=True,
        tracking=True
    )
    orders = fields.Many2many(
        'amanat.order',
        'amanat_order_investment_rel',
        'investment_id',
        'order_id',
        string='Ордеры', 
        tracking=True
    )
    write_offs = fields.Many2many(
        'amanat.writeoff',
        'amanat_investment_writeoff_rel',
        'investment_id',
        'writeoff_id',
        string='Списания (From Ордеры)', 
        tracking=True
    )
    rollup_write_offs = fields.Float(
        string='Ролап списания (From Ордеры)',
        compute='_compute_rollup_write_offs',
        store=True,
        tracking=True,
    )
    rollup_amount = fields.Float(string='Сумма ролап списания', tracking=True)
    create_action = fields.Boolean(string='Создать', tracking=True)
    post = fields.Boolean(string='Провести', tracking=True)
    repost = fields.Boolean(string='Перепровести', tracking=True)
    close_investment = fields.Boolean(string='Закрытия инвестиций', tracking=True)
    today_date = fields.Date(
        string='Дата сегодня',
        compute='_compute_calendar_and_work_days',
        store=True,
        tracking=True
    )
    to_delete = fields.Boolean(string='Пометить на удаление', tracking=True)
    accrue = fields.Boolean(string='Начислить', tracking=True)

    # Роялти
    has_royalty = fields.Boolean(string='Есть роялти?', tracking=True)
    royalty_post = fields.Boolean(string='Провести роялти', tracking=True)

    royalty_recipient_1 = fields.Many2one('amanat.contragent', string='Получатель роялти 1', tracking=True)
    royalty_recipient_2 = fields.Many2one('amanat.contragent', string='Получатель роялти 2', tracking=True)
    royalty_recipient_3 = fields.Many2one('amanat.contragent', string='Получатель роялти 3', tracking=True)
    royalty_recipient_4 = fields.Many2one('amanat.contragent', string='Получатель роялти 4', tracking=True)
    royalty_recipient_5 = fields.Many2one('amanat.contragent', string='Получатель роялти 5', tracking=True)
    royalty_recipient_6 = fields.Many2one('amanat.contragent', string='Получатель роялти 6', tracking=True)
    royalty_recipient_7 = fields.Many2one('amanat.contragent', string='Получатель роялти 7', tracking=True)
    royalty_recipient_8 = fields.Many2one('amanat.contragent', string='Получатель роялти 8', tracking=True)
    royalty_recipient_9 = fields.Many2one('amanat.contragent', string='Получатель роялти 9', tracking=True)

    percent_1 = fields.Float(string='% первого', tracking=True)
    percent_2 = fields.Float(string='% второго', tracking=True)
    percent_3 = fields.Float(string='% третьего', tracking=True)
    percent_4 = fields.Float(string='% четвертого', tracking=True)
    percent_5 = fields.Float(string='% пятого', tracking=True)
    percent_6 = fields.Float(string='% шестого', tracking=True)
    percent_7 = fields.Float(string='% седьмого', tracking=True)
    percent_8 = fields.Float(string='% восьмого', tracking=True)
    percent_9 = fields.Float(string='% девятого', tracking=True)

    royalty_amount_1 = fields.Float(
        string='Сумма роялти 1',
        compute='_compute_royalty_amounts',
        store=True,
        tracking=True
    )
    royalty_amount_2 = fields.Float(
        string='Сумма роялти 2',
        compute='_compute_royalty_amounts',
        store=True,
        tracking=True
    )
    royalty_amount_3 = fields.Float(
        string='Сумма роялти 3',
        compute='_compute_royalty_amounts',
        store=True,
        tracking=True
    )
    royalty_amount_4 = fields.Float(
        string='Сумма роялти 4',
        compute='_compute_royalty_amounts',
        store=True,
        tracking=True
    )
    royalty_amount_5 = fields.Float(
        string='Сумма роялти 5',
        compute='_compute_royalty_amounts',
        store=True,
        tracking=True
    )
    royalty_amount_6 = fields.Float(
        string='Сумма роялти 6',
        compute='_compute_royalty_amounts',
        store=True,
        tracking=True
    )
    royalty_amount_7 = fields.Float(
        string='Сумма роялти 7',
        compute='_compute_royalty_amounts',
        store=True,
        tracking=True
    )
    royalty_amount_8 = fields.Float(
        string='Сумма роялти 8',
        compute='_compute_royalty_amounts',
        store=True,
        tracking=True
    )
    royalty_amount_9 = fields.Float(
        string='Сумма роялти 9',
        compute='_compute_royalty_amounts',
        store=True,
        tracking=True
    )

    rollup_amount_total = fields.Float(string='Сумма RollUp (from Погасить)', tracking=True) # TODO сделать rollup-полем

    # добавить платежку, если нужна

    @api.depends('amount', 'rollup_amount_total')
    def _compute_principal(self):
        for rec in self:
            rec.principal = rec.amount - rec.rollup_amount_total if rec.amount is not None else 0.0

    @api.depends('date')
    def _compute_calendar_and_work_days(self):
        # Static holiday list for workday calculations
        holiday_dates = {
            date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3),
            date(2024, 1, 4), date(2024, 1, 5), date(2024, 1, 6),
            date(2024, 1, 7), date(2024, 1, 8), date(2024, 2, 23),
            date(2024, 3, 8), date(2024, 5, 1), date(2024, 5, 9),
            date(2024, 6, 12), date(2024, 11, 4)
        }
        special_date = date(2024, 12, 28)
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date:
                start_date = rec.date
                # Calendar days inclusive
                delta = today - start_date
                rec.calendar_days = delta.days + 1
                # Work days calculation
                count = 0
                for i in range(delta.days + 1):
                    current = start_date + timedelta(days=i)
                    if current.weekday() < 5 and current not in holiday_dates:
                        count += 1
                # Include special date if in range
                if start_date <= special_date <= today:
                    count += 1
                rec.work_days = count
            else:
                rec.calendar_days = 0
                rec.work_days = 0
            rec.today_date = today

    @api.depends('amount', 'percent_1', 'percent_2', 'percent_3', 'percent_4',
                 'percent_5', 'percent_6', 'percent_7', 'percent_8', 'percent_9')
    def _compute_royalty_amounts(self):
        for rec in self:
            amounts = [
                rec.amount * rec.percent_1,
                rec.amount * rec.percent_2,
                rec.amount * rec.percent_3,
                rec.amount * rec.percent_4,
                rec.amount * rec.percent_5,
                rec.amount * rec.percent_6,
                rec.amount * rec.percent_7,
                rec.amount * rec.percent_8,
                rec.amount * rec.percent_9
            ]
            rec.royalty_amount_1, rec.royalty_amount_2, rec.royalty_amount_3, \
            rec.royalty_amount_4, rec.royalty_amount_5, rec.royalty_amount_6, \
            rec.royalty_amount_7, rec.royalty_amount_8, rec.royalty_amount_9 = amounts

    @api.onchange('sender')
    def _onchange_sender_id(self):
        if self.sender:
            payer = self.env['amanat.payer'].search(
                [('contragents_ids', 'in', self.sender.id)], limit=1)
            self.payer_sender = payer.id if payer else False
        else:
            self.payer_sender = False

    @api.onchange('receiver')
    def _onchange_receiver_id(self):
        if self.receiver:
            payer = self.env['amanat.payer'].search(
                [('contragents_ids', 'in', self.receiver.id)], limit=1)
            self.payer_receiver = payer.id if payer else False
        else:
            self.payer_receiver = False

    @api.depends('orders.rollup_write_off')
    def _compute_rollup_write_offs(self):
        for rec in self:
            rec.rollup_write_offs = sum(
                order.rollup_write_off for order in rec.orders if order.rollup_write_off is not None
            )