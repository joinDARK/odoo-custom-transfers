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
    money_ids = fields.One2many(
        'amanat.money',
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
    ], string='Статус', tracking=True)

    # Привязка к заявке
    zayavka_ids = fields.Many2many(
        'amanat.zayavka',
        'amanat_zayavka_order_rel',
        'order_id',
        'zayavka_id',
        string='Заявки',
        tracking=True
    )
    money = fields.Float(string='Деньги', tracking=True)

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
    gold = fields.Many2many(
        'amanat.gold_deal',
        'amanat_order_gold_deal_rel',
        'order_id',
        'gold_deal_id',
        string='Золото', 
        tracking=True
    )

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
    cross_currency = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЕШ'),
            ('usd', 'USD'), ('usd_cashe', 'USD КЕШ'),
            ('usdt', 'USDT'),
            ('euro', 'EURO'), ('euro_cashe', 'EURO КЕШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЕШ'),
            ('aed', 'AED'), ('aed_cashe', 'AED КЕШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЕШ'),
        ],
        string='Кросс валюта (from Конвертация)',
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
    partner_gold = fields.Many2many(
        'amanat.partner_gold',
        'amanat_order_partner_gold_rel',
        'order_id',
        'partner_gold_id',
        string='Партнеры золото', 
        tracking=True
    )
    write_off = fields.Float(string='Списания', tracking=True)
    @api.depends('money_ids.writeoff_ids.amount')
    def _compute_rollup_write_off(self):
        for rec in self:
            rec.rollup_write_off = sum(w.amount for m in rec.money_ids for w in m.writeoff_ids)

    rollup_write_off = fields.Float(
        string='Роллап списания',
        compute='_compute_rollup_write_off',
        store=True,
        tracking=True
    )
    reconciliation = fields.Float(string='Сверка', tracking=True)
    remaining_debt = fields.Float(
        string='Остаток долга',
        compute='_compute_remaining_debt',
        store=True,
        tracking=True
    )

    # Валютный резерв
    reserve_ids = fields.Many2many(
        'amanat.reserve',
        string="Валютный резерв",
        relation='amanat_order_reserve_rel',
        column1='order_id',
        column2='reserve_id',
        inverse_name='order_ids',
    )

    currency_from_zayavka = fields.Selection([
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'),
            ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
            ('usdt', 'USDT'),
            ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'),
            ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ')
        ],
        string='Валюта (from Заявки)',
        compute='_compute_currency_from_zayavka',
        store=True,
        tracking=True
    )

    converted_sum_from_zayavka = fields.Float(
        string='Сумма после конвертации Заявки',
        compute='_compute_currency_from_zayavka',
        store=True,
        tracking=True
    )

    @api.depends('zayavka_ids.currency', 'amount', 'rate')
    def _compute_currency_from_zayavka(self):
        for rec in self:
            if len(rec.zayavka_ids) == 1:
                zayavka = rec.zayavka_ids[0]
                rec.currency_from_zayavka = zayavka.currency
                rec.converted_sum_from_zayavka = rec.amount * rec.rate if rec.amount and rec.rate else 0.0
            else:
                rec.currency_from_zayavka = False
                rec.converted_sum_from_zayavka = 0.0

    DIRECT_RULES = {
        ('aed', 'aed'): 'mul',
        ('aed', 'aed_cashe'): 'mul',
        ('aed', 'cny'): 'mul',
        ('aed', 'cny_cashe'): 'mul',
        ('aed', 'euro'): 'div',
        ('aed', 'euro_cashe'): 'div',
        ('aed', 'rub'): 'mul',
        ('aed', 'rub_cashe'): 'mul',
        ('aed', 'usd'): 'div',
        ('aed', 'usd_cashe'): 'div',
        ('aed', 'usdt'): 'div',
        ('cny', 'aed'): 'mul',
        ('cny', 'aed_cashe'): 'mul',
        ('cny', 'cny'): 'mul',
        ('cny', 'cny_cashe'): 'mul',
        ('cny', 'euro'): 'mul',
        ('cny', 'euro_cashe'): 'mul',
        ('cny', 'rub'): 'mul',
        ('cny', 'rub_cashe'): 'mul',
        ('cny', 'usd'): 'mul',
        ('cny', 'usd_cashe'): 'mul',
        ('cny', 'usdt'): 'mul',
        ('cny_cashe', 'aed'): 'mul',
        ('cny_cashe', 'aed_cashe'): 'mul',
        ('cny_cashe', 'cny'): 'mul',
        ('cny_cashe', 'cny_cashe'): 'mul',
        ('cny_cashe', 'euro'): 'mul',
        ('cny_cashe', 'euro_cashe'): 'mul',
        ('cny_cashe', 'rub'): 'mul',
        ('cny_cashe', 'rub_cashe'): 'mul',
        ('cny_cashe', 'usd'): 'mul',
        ('cny_cashe', 'usd_cashe'): 'mul',
        ('cny_cashe', 'usdt'): 'mul',
        ('euro', 'aed'): 'mul',
        ('euro', 'aed_cashe'): 'mul',
        ('euro', 'cny'): 'mul',
        ('euro', 'cny_cashe'): 'mul',
        ('euro', 'euro'): 'mul',
        ('euro', 'euro_cashe'): 'mul',
        ('euro', 'rub'): 'mul',
        ('euro', 'rub_cashe'): 'mul',
        ('euro', 'usd'): 'mul',
        ('euro', 'usd_cashe'): 'mul',
        ('euro', 'usdt'): 'mul',
        ('euro_cashe', 'aed'): 'mul',
        ('euro_cashe', 'aed_cashe'): 'mul',
        ('euro_cashe', 'cny'): 'mul',
        ('euro_cashe', 'cny_cashe'): 'mul',
        ('euro_cashe', 'euro'): 'mul',
        ('euro_cashe', 'euro_cashe'): 'mul',
        ('euro_cashe', 'rub'): 'mul',
        ('euro_cashe', 'rub_cashe'): 'mul',
        ('euro_cashe', 'usd'): 'mul',
        ('euro_cashe', 'usd_cashe'): 'mul',
        ('euro_cashe', 'usdt'): 'mul',
        ('rub', 'aed'): 'mul',
        ('rub', 'aed_cashe'): 'mul',
        ('rub', 'cny'): 'div',
        ('rub', 'cny_cashe'): 'div',
        ('rub', 'euro'): 'div',
        ('rub', 'euro_cashe'): 'div',
        ('rub', 'rub'): 'mul',
        ('rub', 'rub_cashe'): 'mul',
        ('rub', 'usd'): 'div',
        ('rub', 'usd_cashe'): 'div',
        ('rub', 'usdt'): 'div',
        ('rub_cashe', 'aed'): 'mul',
        ('rub_cashe', 'aed_cashe'): 'mul',
        ('rub_cashe', 'cny'): 'div',
        ('rub_cashe', 'cny_cashe'): 'div',
        ('rub_cashe', 'euro'): 'div',
        ('rub_cashe', 'euro_cashe'): 'div',
        ('rub_cashe', 'rub'): 'mul',
        ('rub_cashe', 'rub_cashe'): 'mul',
        ('rub_cashe', 'usd'): 'div',
        ('rub_cashe', 'usd_cashe'): 'div',
        ('rub_cashe', 'usdt'): 'div',
        ('usd', 'aed'): 'mul',
        ('usd', 'aed_cashe'): 'mul',
        ('usd', 'cny'): 'mul',
        ('usd', 'cny_cashe'): 'mul',
        ('usd', 'euro'): 'mul',
        ('usd', 'euro_cashe'): 'mul',
        ('usd', 'rub'): 'mul',
        ('usd', 'rub_cashe'): 'mul',
        ('usd', 'usd'): 'mul',
        ('usd', 'usd_cashe'): 'mul',
        ('usd', 'usdt'): 'mul',
        ('usd_cashe', 'aed'): 'mul',
        ('usd_cashe', 'aed_cashe'): 'mul',
        ('usd_cashe', 'cny'): 'mul',
        ('usd_cashe', 'cny_cashe'): 'mul',
        ('usd_cashe', 'euro'): 'mul',
        ('usd_cashe', 'euro_cashe'): 'mul',
        ('usd_cashe', 'rub'): 'mul',
        ('usd_cashe', 'rub_cashe'): 'mul',
        ('usd_cashe', 'usd'): 'mul',
        ('usd_cashe', 'usd_cashe'): 'mul',
        ('usd_cashe', 'usdt'): 'mul',
        ('usdt', 'aed'): 'mul',
        ('usdt', 'aed_cashe'): 'mul',
        ('usdt', 'cny'): 'mul',
        ('usdt', 'cny_cashe'): 'mul',
        ('usdt', 'euro'): 'mul',
        ('usdt', 'euro_cashe'): 'mul',
        ('usdt', 'rub'): 'mul',
        ('usdt', 'rub_cashe'): 'mul',
        ('usdt', 'usd'): 'mul',
        ('usdt', 'usd_cashe'): 'mul',
        ('usdt', 'usdt'): 'mul',
    }

    CROSS_RULES_STAGE_1 = {
        ('usdt', 'rub'): 'mul',
        ('usdt', 'usd'): 'mul',
        ('usd', 'rub'): 'mul',
        ('usd', 'usd'): 'mul',
        ('usd_cashe', 'rub'): 'mul',
        ('usd_cashe', 'usd'): 'mul',
        ('euro', 'rub'): 'mul',
        ('euro', 'usd'): 'mul',
        ('euro_cashe', 'rub'): 'mul',
        ('euro_cashe', 'usd'): 'mul',
        ('cny', 'rub'): 'mul',
        ('cny', 'usd'): 'mul',
        ('cny_cashe', 'rub'): 'mul',
        ('cny_cashe', 'usd'): 'mul',
        ('aed', 'rub'): 'mul',
        ('aed', 'usd'): 'div',
        ('aed_cashe', 'rub'): 'mul',
        ('aed_cashe', 'usd'): 'div',
        ('rub', 'usd'): 'div',
        ('rub_cashe', 'usd'): 'div',
    }

    CROSS_RULES_STAGE_2 = {
        ('rub', 'euro'): 'div',
        ('rub', 'euro_cashe'): 'div',
        ('rub', 'cny'): 'div',
        ('rub', 'cny_cashe'): 'div',
        ('rub', 'aed'): 'mul',
        ('rub', 'aed_cashe'): 'mul',
        ('rub', 'rub_cashe'): 'mul',
        ('rub', 'rub'): 'mul',
        ('rub', 'usd'): 'div',
        ('rub', 'usd_cashe'): 'div',
        ('rub', 'usdt'): 'div',
        ('usd', 'rub'): 'mul',
        ('usd', 'rub_cashe'): 'mul',
        ('usd', 'euro'): 'mul',
        ('usd', 'euro_cashe'): 'mul',
        ('usd', 'cny'): 'mul',
        ('usd', 'cny_cashe'): 'mul',
        ('usd', 'aed'): 'mul',
        ('usd', 'aed_cashe'): 'mul',
        ('usd', 'usdt'): 'mul',
        ('usd', 'usd_cashe'): 'mul',
        ('usd', 'usd'): 'mul',
    }

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
        'conversion_ids.rate',
        'conversion_ids.currency',
        'conversion_ids.conversion_currency',
        'conversion_ids.cross_conversion_currency',
        'amount',
    )
    def _compute_conversion_fields(self):
        for rec in self:
            # нет конверсий — обнуляем
            if not rec.conversion_ids:
                rec.cross_from = False
                rec.cross_rate = 0.0
                rec.currency_from_conv = False
                rec.currency_to_copy = False
                rec.cross_currency = False
                rec.cross_calc = 0.0
                rec.amount_after_conv = 0.0
                continue

            # ищем кросс-конверсию
            cross = rec.conversion_ids.filtered('cross_envelope')
            if cross:
                c = cross[0]
                rec.cross_from = True
                rec.cross_rate = c.cross_rate or 0.0
                rec.currency_from_conv = c.currency
                rec.currency_to_copy = c.conversion_currency
                rec.cross_currency = c.cross_conversion_currency

                # 1) Шаг 1: currency → cross_currency через cross_rate
                key1 = (c.currency, c.cross_conversion_currency)
                action1 = self.CROSS_RULES_STAGE_1.get(key1, 'mul')
                if action1 == 'mul':
                    rec.cross_calc = rec.amount * (c.cross_rate or 1.0)
                else:
                    rec.cross_calc = rec.amount / (c.cross_rate or 1.0)

                # 2) Шаг 2: cross_currency → conversion_currency через rate
                key2 = (c.cross_conversion_currency, c.conversion_currency)
                action2 = self.CROSS_RULES_STAGE_2.get(key2, 'mul')
                if action2 == 'mul':
                    rec.amount_after_conv = rec.cross_calc * (c.rate or 1.0)
                else:
                    rec.amount_after_conv = rec.cross_calc / (c.rate or 1.0)

            else:
                # прямая конвертация (без кросс)
                c2 = rec.conversion_ids[0]
                rec.cross_from = False
                rec.cross_rate = 0.0
                rec.currency_from_conv = c2.currency
                rec.currency_to_copy = c2.conversion_currency
                rec.cross_currency = False

                rec.cross_calc = rec.amount
                key = (c2.currency, c2.conversion_currency)
                action = self.DIRECT_RULES.get(key, 'mul')
                if action == 'mul':
                    rec.amount_after_conv = rec.cross_calc * (c2.rate or 1.0)
                else:
                    rec.amount_after_conv = rec.cross_calc / (c2.rate or 1.0)

    def _get_realtime_fields(self):
        """Поля для real-time обновлений в списке ордеров"""
        return [
            'id', 'display_name', 'name', 'date', 'type', 'currency', 'amount',
            'partner_1_id', 'partner_2_id', 'payer_1_id', 'payer_2_id',
            'wallet_1_id', 'wallet_2_id', 'status', 'is_confirmed',
            'comment', 'rate', 'operation_percent', 'our_percent',
            'rko', 'amount_1', 'rko_2', 'amount_2', 'total',
            'create_date', 'write_date'
        ]

    @api.depends('money_ids.remains')
    def _compute_remaining_debt(self):
        for rec in self:
            rec.remaining_debt = sum(rec.money_ids.mapped('remains'))

    def action_update_rollup_write_off(self):
        """
        Ручной пересчёт rollup_write_off: суммирует все списания по всем контейнерам этого ордера
        """
        Writeoff = self.env['amanat.writeoff']
        for rec in self:
            writeoffs = Writeoff.search([('money_id.order_id', '=', rec.id)])
            rec.rollup_write_off = sum(writeoffs.mapped('amount'))
        return True

    def button_update_rollup_write_off(self):
        self.ensure_one()
        self.action_update_rollup_write_off()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rollup списания обновлён'),
                'message': _('Сумма rollup списания успешно пересчитана.'),
                'type': 'success',
                'sticky': False,
            }
        }

    