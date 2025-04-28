# models/order.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Order(models.Model, AmanatBaseModel):
    _name = 'amanat.order'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Ордер'

    name = fields.Char(string='ID ордера', readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('amanat.order.sequence'), copy=False)

    date = fields.Date(
        string='Дата', 
        tracking=True, 
        default=fields.Date.today
    )
    type = fields.Selection([
        ('transfer', 'Перевод'),
        ('payment', 'Оплата'),
        ('royalty', 'Роялти'),
        ],
        string='Тип',
        tracking=True,
    )

    transfer_id = fields.Many2many(
        'amanat.transfer',
        'amanat_transfer_order_rel',
        'order_id',
        'transfer_id',
        string="Перевод",
        tracking=True,
    )
    money_ids = fields.Many2many(
        'amanat.money', 
        'amanat_order_money_rel', 
        'money_id',
        'order_id',
        string="Деньги",
        tracking=True,
    )
    sverka_ids = fields.Many2many(
        'amanat.reconciliation',
        'amanat_order_reconciliation_rel', 
        'reconciliation_id',
        'order_id', 
        string="Сверка",
        tracking=True,
    )

    # Участники
    partner_1_id = fields.Many2one('amanat.contragent', string='Контрагент 1', tracking=True)
    payer_1_id = fields.Many2one('amanat.payer', string='Плательщик 1', tracking=True) # Нужно разобраться с выбором только связанных контрагентов в таблице Ордер
    wallet_1_id = fields.Many2one('amanat.wallet', string='Кошелек 1', tracking=True)

    partner_2_id = fields.Many2one('amanat.contragent', string='Контрагент 2', tracking=True)
    payer_2_id = fields.Many2one('amanat.payer', string='Плательщик 2', tracking=True) # Нужно разобраться с выбором только связанных контрагентов в таблице Ордер
    wallet_2_id = fields.Many2one('amanat.wallet', string='Кошелек 2', tracking=True)

    # Финансы
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
    amount = fields.Float(string='Сумма', tracking=True)
    rate = fields.Float(string='Курс', tracking=True)
    operation_percent = fields.Float(string='% За операцию', tracking=True)
    our_percent = fields.Float(string='Наш % за операцию', tracking=True)

    rko = fields.Float(
        string='РКО',
        compute='_compute_financials',
        store=True,
        tracking=True
    )
    amount_1 = fields.Float(
        string='Сумма 1',
        compute='_compute_financials',
        store=True,
        tracking=True
    )
    rko_2 = fields.Float(
        string='РКО 2',
        compute='_compute_financials',
        store=True,
        tracking=True
    )
    amount_2 = fields.Float(
        string='Сумма 2',
        compute='_compute_financials',
        store=True,
        tracking=True
    )
    total = fields.Float(
        string='ИТОГО',
        compute='_compute_financials',
        store=True,
        tracking=True
    )

    # Прочее
    comment = fields.Text(string='Комментарий', tracking=True)
    is_confirmed = fields.Boolean(string='Провести', tracking=True)
    status = fields.Selection([
        ('draft', 'Черновик'),
        ('confirmed', 'Подтверждено'),
        ('done', 'Выполнено'),
    ], string='Статус', default='draft', tracking=True)

    # Привязка к заявке
    money = fields.Float(string='Деньги', tracking=True)
    converted_amount = fields.Float(string='Валюта(из заявки)', tracking=True)

    # Инвестиции
    investment = fields.Many2many(
        'amanat.investment',
        'amanat_order_investment_rel',
        'order_id',
        'investment_id',
        string='Инвестиция', 
        tracking=True
    )

    # Золото
    gold = fields.Float(string='Золото', tracking=True)

    # Конвертация
    conversion_ids = fields.Many2many(
        'amanat.conversion',
        'amanat_order_conversion_rel',
        'order_id',
        'conversion_id',
        string='Конвертация',
        tracking=True,
    )

    # lookup-поля
    cross_from = fields.Boolean(
        string='Кросс-конверт (from Конвертация)',
        compute='_compute_conversion_fields', store=True
    )
    cross_rate = fields.Float(
        string='Крос-Курс (from Конвертация)',
        compute='_compute_conversion_fields', store=True
    )
    currency_from_conv = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЕШ'),
            ('usd', 'USD'), ('usd_cashe', 'USD КЕШ'),
            ('usdt', 'USDT'),
            ('euro', 'EURO'), ('euro_cashe', 'EURO КЕШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЕШ'),
            ('aed', 'AED'), ('aed_cashe', 'AED КЕШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЕШ'),
        ],
        string='Валюта (from Конвертация)',
        compute='_compute_conversion_fields', store=True
    )
    currency_to_copy = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЕШ'),
            ('usd', 'USD'), ('usd_cashe', 'USD КЕШ'),
            ('usdt', 'USDT'),
            ('euro', 'EURO'), ('euro_cashe', 'EURO КЕШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЕШ'),
            ('aed', 'AED'), ('aed_cashe', 'AED КЕШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЕШ'),
        ],
        string='В какую валюту (from Конвертация)',
        compute='_compute_conversion_fields', store=True
    )

    # formula-поля
    cross_calc = fields.Float(
        string='Подсчет крос',
        compute='_compute_conversion_fields', store=True
    )
    amount_after_conv = fields.Float(
        string='Сумма после конвертации',
        compute='_compute_conversion_fields', store=True
    )

    # Финал
    partner_gold = fields.Float(string='Партнеры золото', tracking=True)
    write_off = fields.Float(string='Списания', tracking=True)
    rollup_write_off = fields.Float(string='Роллап списания', tracking=True)
    reconciliation = fields.Float(string='Сверка', tracking=True)
    remaining_debt = fields.Float(string='Остаток долга', tracking=True)

    # Валютный резерв
    reserve_ids = fields.Many2many(
        'amanat.reserve',
        string="Валютный резерв",
        relation='amanat_order_reserve_rel',
        column1='order_id',
        column2='reserve_id',
        inverse_name='order_ids',
    )

    @api.depends('amount', 'operation_percent', 'our_percent')
    def _compute_financials(self):
        for rec in self:
            # Вычисляем РКО по проценту операции
            rec.rko = rec.amount * rec.operation_percent
            # Вычисляем Сумму 1 по условию
            if rec.operation_percent < 0:
                rec.amount_1 = rec.amount
            else:
                rec.amount_1 = rec.amount - rec.rko
            # Вычисляем РКО 2 по нашему проценту
            rec.rko_2 = rec.amount * rec.our_percent
            # Вычисляем Сумму 2 по условию
            if rec.operation_percent < 0:
                rec.amount_2 = rec.amount - rec.rko
            else:
                rec.amount_2 = rec.amount - rec.rko_2
            # Вычисляем общий итог
            rec.total = rec.amount - rec.rko

    @api.depends(
        'conversion_ids.cross_envelope',
        'conversion_ids.cross_rate',
        'conversion_ids.currency',
        'conversion_ids.conversion_currency',
        'amount', 'rate'
    )
    
    def _compute_conversion_fields(self):
        base_div = {'rub', 'rub_cashe', 'thb', 'thb_cashe', 'aed', 'aed_cashe'}
        target_div = {'usd', 'usd_cashe', 'euro', 'euro_cashe', 'usdt', 'cny', 'cny_cashe'}
        for rec in self:
            # первая кроссовая конверсия
            cross = rec.conversion_ids.filtered('cross_envelope')
            if cross:
                c = cross[0]
                rec.cross_from = True
                rec.cross_rate = c.cross_rate
                rec.currency_from_conv = c.currency
                rec.currency_to_copy = c.conversion_currency
                # расчёт cross_calc
                if c.currency in base_div and c.conversion_currency in target_div:
                    rec.cross_calc = rec.amount / (c.cross_rate or 1.0)
                else:
                    rec.cross_calc = rec.amount * (c.cross_rate or 1.0)
                # расчёт amount_after_conv
                if c.conversion_currency in base_div and c.currency in target_div:
                    rec.amount_after_conv = rec.cross_calc / (c.rate or 1.0)
                else:
                    rec.amount_after_conv = rec.cross_calc * (c.rate or 1.0)
            elif rec.conversion_ids:
                # обычная первая конверсия
                c2 = rec.conversion_ids[0]
                rec.cross_from = False
                rec.cross_rate = 0.0
                rec.currency_from_conv = c2.currency
                rec.currency_to_copy = c2.conversion_currency
                rec.cross_calc = rec.amount
                if c2.currency in base_div and c2.conversion_currency in target_div:
                    rec.amount_after_conv = rec.amount / (c2.rate or 1.0)
                else:
                    rec.amount_after_conv = rec.amount * (c2.rate or 1.0)
            else:
                rec.cross_from = False
                rec.cross_rate = 0.0
                rec.currency_from_conv = False
                rec.currency_to_copy = False
                rec.cross_calc = 0.0
                rec.amount_after_conv = 0.0


    @api.depends('amount', 'operation_percent', 'our_percent')
    def _compute_financials(self):
        for rec in self:
            rec.rko = rec.amount * rec.operation_percent
            rec.amount_1 = rec.amount if rec.operation_percent < 0 else rec.amount - rec.rko
            rec.rko_2 = rec.amount * rec.our_percent
            rec.amount_2 = rec.amount - rec.rko if rec.operation_percent < 0 else rec.amount - rec.rko_2
            rec.total = rec.amount - rec.rko