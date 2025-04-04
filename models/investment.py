 # models/investment.py
from odoo import models, fields
from .base_model import AmanatBaseModel


class Investment(models.Model, AmanatBaseModel):
    _name = 'amanat.investment'
    _description = 'Инвестиции'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    id = fields.Char(string='ID', readonly=True)  # Был Integer
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
    date = fields.Date(string='Дата', tracking=True)
    date_close = fields.Date(string='Дата закрытия', tracking=True)
    sender = fields.Many2one('amanat.contragent', string='Отправитель', tracking=True)  # Был Char
    payer_sender = fields.Many2one('amanat.payer', string='Плательщик отправитель', tracking=True)  # Был Char
    receiver = fields.Many2one('amanat.contragent', string='Получатель', tracking=True)  # Был Char
    payer_receiver = fields.Many2one('amanat.payer', string='Плательщик получатель', tracking=True)  # Был Char
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
    fixed_amount = fields.Float(string='Фикс сумма', tracking=True)  # новое поле
    principal = fields.Float(string='Тело долга', tracking=True)
    calendar_days = fields.Integer(string='Календарных дней', tracking=True)
    work_days = fields.Integer(string='Рабочих дней', tracking=True)
    orders = fields.Text(string='Ордеры', tracking=True)
    write_offs = fields.Text(string='Списания (From Ордеры)', tracking=True)
    rollup_write_offs = fields.Text(string='Ролап списания (From Ордеры)', tracking=True)
    rollup_amount = fields.Float(string='Сумма ролап списания', tracking=True)
    create_action = fields.Boolean(string='Создать', tracking=True)
    post = fields.Boolean(string='Провести', tracking=True)
    repost = fields.Boolean(string='Перепровести', tracking=True)
    close_investment = fields.Boolean(string='Закрытия инвестиций', tracking=True)
    today_date = fields.Date(string='Дата сегодня', tracking=True)
    to_delete = fields.Boolean(string='Пометить на удаление', tracking=True)
    accrue = fields.Boolean(string='Начислить', tracking=True)
    has_royalty = fields.Boolean(string='Есть роялти?', tracking=True)
    royalty_post = fields.Boolean(string='Провести роялти', tracking=True)
    royalty_receiver = fields.Char(string='Получатель роялти', tracking=True)
    percent_1 = fields.Float(string='% первого', tracking=True)
    percent_2 = fields.Float(string='% второго', tracking=True)
    percent_3 = fields.Float(string='% третьего', tracking=True)
    percent_4 = fields.Float(string='% четвертого', tracking=True)
    percent_5 = fields.Float(string='% пятого', tracking=True)
    percent_6 = fields.Float(string='% шестого', tracking=True)
    percent_7 = fields.Float(string='% седьмого', tracking=True)
    percent_8 = fields.Float(string='% восьмого', tracking=True)
    percent_9 = fields.Float(string='% девятого', tracking=True)
    royalty_amount_1 = fields.Float(string='Сумма роялти 1', tracking=True)
    royalty_amount_2 = fields.Float(string='Сумма роялти 2', tracking=True)
    royalty_amount_3 = fields.Float(string='Сумма роялти 3', tracking=True)
    royalty_amount_4 = fields.Float(string='Сумма роялти 4', tracking=True)
    royalty_amount_5 = fields.Float(string='Сумма роялти 5', tracking=True)
    royalty_amount_6 = fields.Float(string='Сумма роялти 6', tracking=True)
    royalty_amount_7 = fields.Float(string='Сумма роялти 7', tracking=True)
    royalty_amount_8 = fields.Float(string='Сумма роялти 8', tracking=True)
    royalty_amount_9 = fields.Float(string='Сумма роялти 9', tracking=True)
    rollup_amount_total = fields.Float(string='Сумма RollUp (from Погасить)', tracking=True)