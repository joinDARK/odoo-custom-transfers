# models/money.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Money(models.Model, AmanatBaseModel):
    _name = 'amanat.money'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Контейнеры денег'

    royalty = fields.Boolean(string='Роялти', tracking=True, default=False)
    percent = fields.Boolean(string='Проценты', tracking=True, default=False)
    date = fields.Date(string='Дата', tracking=True)
    wallet_id = fields.Many2one('amanat.wallet', string='Кошелек', tracking=True)
    partner_id = fields.Many2one('amanat.contragent', string='Держатель', tracking=True)
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
    
    # Списания, связанные по money_id
    writeoff_ids = fields.One2many(
        comodel_name='amanat.writeoff',
        inverse_name='money_id',
        string="Списания"
    )

    amount = fields.Float(string='Сумма', tracking=True)
    order_id = fields.Many2one('amanat.order', string='Заявка', tracking=True)
    state = fields.Selection([('debt', 'Долг'), ('positive', 'Положительный')], string='Состояние', tracking=True)

    remains = fields.Float(string='Остаток', tracking=True)
    remains_rub = fields.Float(string='Остаток RUB', tracking=True)
    remains_rub_cashe = fields.Float(string='Остаток RUB КЭШ', tracking=True)
    remains_usd = fields.Float(string='Остаток USD', tracking=True)
    remains_usd_cashe = fields.Float(string='Остаток USD КЭШ', tracking=True)
    remains_usdt = fields.Float(string='Остаток USDT', tracking=True)
    remains_cny = fields.Float(string='Остаток CNY', tracking=True)
    remains_cny_cashe = fields.Float(string='Остаток CNY КЭШ', tracking=True)
    remains_euro = fields.Float(string='Остаток EURO', tracking=True)
    remains_euro_cashe = fields.Float(string='Остаток EURO КЭШ', tracking=True)
    remains_aed = fields.Float(string='Остаток AED', tracking=True)
    remains_aed_cashe = fields.Float(string='Остаток AED КЭШ', tracking=True)
    remains_thb = fields.Float(string='Остаток THB', tracking=True)
    remains_thb_cashe = fields.Float(string='Остаток THB КЭШ', tracking=True)

    sum = fields.Float(string='Сумма', tracking=True)
    sum_rub = fields.Float(string='Сумма RUB', tracking=True)
    sum_usd = fields.Float(string='Сумма USD', tracking=True)
    sum_usdt = fields.Float(string='Сумма USDT', tracking=True)
    sum_cny = fields.Float(string='Сумма CNY', tracking=True)
    sum_euro = fields.Float(string='Сумма EURO', tracking=True)
    sum_aed = fields.Float(string='Сумма AED', tracking=True)
    sum_thb = fields.Float(string='Сумма THB', tracking=True)
    sum_usd_cashe = fields.Float(string='Сумма USD КЭШ', tracking=True)
    sum_euro_cashe = fields.Float(string='Сумма EURO КЭШ', tracking=True)
    sum_aed_cashe = fields.Float(string='Сумма AED КЭШ', tracking=True)
    sum_cny_cashe = fields.Float(string='Сумма CNY КЭШ', tracking=True)
    sum_rub_cashe = fields.Float(string='Сумма RUB КЭШ', tracking=True)
    sum_thb_cashe = fields.Float(string='Сумма THB КЭШ', tracking=True)

    sum_remains = fields.Float(string='Сумма списания', tracking=True)