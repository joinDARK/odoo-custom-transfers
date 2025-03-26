# models/order.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Order(models.Model, AmanatBaseModel):
    _name = 'amanat.order'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Ордер'

    name = fields.Char(string='ID ордера', readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('amanat.order'), copy=False)

    date = fields.Date(string='Дата', tracking=True, required=True)
    type = fields.Selection(
        [('transfer', 'Перевод')],
        string='Тип',
        tracking=True,
        required=True
    )

    # Участники
    partner_1_id = fields.Many2one('amanat.contragent', string='Контрагент 1', tracking=True)
    payer_1_id = fields.Many2one('amanat.payer', string='Плательщик 1', tracking=True)
    wallet_1_id = fields.Many2one('amanat.wallet', string='Кошелек 1', tracking=True)

    partner_2_id = fields.Many2one('amanat.contragent', string='Контрагент 2', tracking=True)
    payer_2_id = fields.Many2one('amanat.payer', string='Плательщик 2', tracking=True)
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
    rko = fields.Float(string='РКО', tracking=True)
    amount_1 = fields.Float(string='Сумма 1', tracking=True)
    our_percent = fields.Float(string='Наш % за операцию', tracking=True)
    rko_2 = fields.Float(string='РКО 2', tracking=True)
    amount_2 = fields.Float(string='Сумма 2', tracking=True)
    total = fields.Float(string='ИТОГО', tracking=True)

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
    reserve_1 = fields.Float(string='Валютный резерв 1', tracking=True)

    converted_amount = fields.Float(string='Валюта(из заявки)', tracking=True)

    # Инвестиции
    investment = fields.Float(string='Инвестиция', tracking=True)
    gold = fields.Float(string='Золото', tracking=True)

    # Кросс-конвертация
    cross_from = fields.Float(string='Крос-конверт (из Конвертации)', tracking=True)
    cross_rate = fields.Float(string='Крос-курс (из Конвертации)', tracking=True)
    cross_currency_from = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'), ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'), ('usdt', 'USDT'), ('euro', 'EURO'),
            ('euro_cashe', 'EURO КЭШ'), ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'), ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
        ],
        string='Валюта (Из конвертации)',
        default='rub',
        tracking=True
    )
    cross_currency_to = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'), ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'), ('usdt', 'USDT'), ('euro', 'EURO'),
            ('euro_cashe', 'EURO КЭШ'), ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'), ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
        ],
        string='В какую валюту',
        default='rub',
        tracking=True
    )
    cross_calc = fields.Float(string='Подсчет крос', tracking=True)
    cross_converted = fields.Float(string='Сумма после конвертации (Крос)', tracking=True)

    # Финал
    partner_gold = fields.Float(string='Партнеры золото', tracking=True)
    write_off = fields.Float(string='Списания', tracking=True)
    rollup_write_off = fields.Float(string='Роллап списания', tracking=True)
    reconciliation = fields.Float(string='Сверка', tracking=True)
    remaining_debt = fields.Float(string='Остаток долга', tracking=True)