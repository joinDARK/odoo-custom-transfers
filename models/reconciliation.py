# models/reconciliation.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Reconciliation(models.Model, AmanatBaseModel):
    _name = 'amanat.reconciliation'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Сверки'

    date = fields.Date(string='Дата', tracking=True)
    partner_id = fields.Many2one('amanat.contragent', string='Контрагент', tracking=True)
    currency = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'), ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'), ('usdt', 'USDT'), ('euro', 'EURO'),
            ('euro_cashe', 'EURO КЭШ'), ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'), ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
        ],
        string='Валюта',
        default='rub',
        tracking=True
    )
    sum = fields.Float(string='Сумма', tracking=True)
    wallet_id = fields.Many2one('amanat.wallet', string='Кошелек', tracking=True)
    sender_id = fields.Many2many(
        'amanat.payer',
        string='Отправитель',
        tracking=True
    )
    sender_contragent = fields.Many2many(
        'amanat.contragent',
        related='sender_id.contragents_ids',
        string='Отправитель (from Контрагент)',
        tracking=True
    )
    receiver_id = fields.Many2many(
        'amanat.payer',
        'amanat_reconciliation_payer_rel',
        'reconciliation_id',
        'payer_id',
        string='Получатель',
        tracking=True
    )
    receiver_contragent = fields.Many2many(
        'amanat.contragent',
        related='receiver_id.contragents_ids',
        string='Получатель (from Контрагент)',
        tracking=True
    )

    sum_rub = fields.Float(string='Сумма RUB', tracking=True)
    sum_usd = fields.Float(string='Сумма USD', tracking=True)
    sum_usdt = fields.Float(string='Сумма USDT', tracking=True)
    sum_cny = fields.Float(string='Сумма CNY', tracking=True)
    sum_euro = fields.Float(string='Сумма EURO', tracking=True)
    sum_aed = fields.Float(string='Сумма AED', tracking=True)
    sum_thb = fields.Float(string='Сумма THB', tracking=True)

    sum_rub_cashe = fields.Float(string='Сумма RUB КЭШ', tracking=True)
    sum_usd_cashe = fields.Float(string='Сумма USD КЭШ', tracking=True)
    sum_cny_cashe = fields.Float(string='Сумма CNY КЭШ', tracking=True)
    sum_euro_cashe = fields.Float(string='Сумма EURO КЭШ', tracking=True)
    sum_aed_cashe = fields.Float(string='Сумма AED КЭШ', tracking=True)
    sum_thb_cashe = fields.Float(string='Сумма THB КЭШ', tracking=True)

    rate = fields.Float(string='Курс', related='order_id.rate', store=True, tracking=True)
    award = fields.Float(string='За операцию (from Ордер)', related='order_id.operation_percent', store=True, tracking=True)
    rko = fields.Float(string='РКО (from Ордер)', related='order_id.rko', store=True, tracking=True)
    our_percent = fields.Float(string='Наш процент (from Ордер)', related='order_id.our_percent', store=True, tracking=True)
    rko_2 = fields.Float(string='РКО 2 (from Ордер)', related='order_id.rko_2', store=True, tracking=True)
    
    exchange = fields.Float(string='К выдаче', tracking=True)
    order_id = fields.Many2many(
        'amanat.order',
        'amanat_order_reconciliation_rel',
        'order_id', 
        'reconciliation_id',
        string='Ордер', 
        tracking=True
    )
    order_comment = fields.Text(string='Комментарий (from Ордер)', related='order_id.comment', store=True, tracking=True)
    unload = fields.Boolean(string='Выгрузить', default=False, tracking=True)

    range = fields.Many2one('amanat.ranges', string='Диапазон', tracking=True)
    range_reconciliation_date_1 = fields.Date(string='Сверка Дата 1 (from Диапазон)', related='range.reconciliation_date_1', store=True, tracking=True)
    range_reconciliation_date_2 = fields.Date(string='Сверка Дата 2 (from Диапазон)', related='range.reconciliation_date_2', store=True, tracking=True)
    range_date_reconciliation = fields.Selection(
        [('not', 'Нет'), ('yes', 'Да')],
        string='Диапазон дат сверка',
        default='not',
        tracking=True
    )
    compare_balance_date_1 = fields.Date(string='Сравнение баланса дата 1 (from Диапазон)', related='range.compare_balance_date_1', store=True, tracking=True)
    compare_balance_date_2 = fields.Date(string='Сравнение баланса дата 2 (from Диапазон)', related='range.compare_balance_date_2', store=True, tracking=True)
    status_comparison_1 = fields.Selection(
        [('not', 'Нет'), ('yes', 'Да')],
        string='Статус сравнение 1',
        default='not',
        tracking=True
    )
    status_comparison_2 = fields.Selection(
        [('not', 'Нет'), ('yes', 'Да')],
        string='Статус сравнение 2',
        default='not',
        tracking=True
    )
    range_date_start = fields.Date(string='Дата начало (from Диапазон)', related='range.date_start', store=True, tracking=True)
    range_date_end = fields.Date(string='Дата конец (from Диапазон)', related='range.date_end', store=True, tracking=True)
    status_range = fields.Selection(
        [('not', 'Нет'), ('yes', 'Да')],
        string='Статус диапазона',
        default='not',
        tracking=True
    )

    rate_id = fields.Many2one('amanat.rates', string='Курсы', tracking=True)
    rate_euro = fields.Float(string='euro (from Курсы)', related='rate_id.euro', store=True, tracking=True)
    rate_cny = fields.Float(string='cny (from Курсы)', related='rate_id.cny', store=True, tracking=True)
    rate_rub = fields.Float(string='rub (from Курсы)', related='rate_id.rub', store=True, tracking=True)
    rate_aed = fields.Float(string='aed (from Курсы)', related='rate_id.aed', store=True, tracking=True)
    rate_thb = fields.Float(string='thb (from Курсы)', related='rate_id.thb', store=True, tracking=True)
    rate_usd = fields.Float(string='usd (from Курсы)', related='rate_id.usd', store=True, tracking=True)
    rate_usdt = fields.Float(string='usdt (from Курсы)', related='rate_id.usdt', store=True, tracking=True)
    equivalent = fields.Float(string='Эквивалент $', tracking=True)

    create_Reconciliation = fields.Boolean(string='Создать', default=False, tracking=True)
    royalti_Reconciliation = fields.Boolean(string='Провести роялти', default=False, tracking=True)
    