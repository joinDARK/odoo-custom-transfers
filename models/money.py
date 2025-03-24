# models/money.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Money(models.Model, AmanatBaseModel):
    _name = 'amanat.money'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Контейнеры денег'

    date = fields.Date(string='Дата', tracking=True)
    wallet_id = fields.Many2one('amanat.wallet', string='Кошелек', tracking=True)
    partner_id = fields.Many2one('amanat.contragent', string='Партнер', tracking=True)
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
    order_id = fields.Many2one('amanat.order', string='Заявка', tracking=True)
    state = fields.Selection([('debt', 'Долг'), ('positive', 'Положительный')], string='Состояние', tracking=True)