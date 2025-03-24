# models/order.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Order(models.Model, AmanatBaseModel):
    _name = 'amanat.order'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Ордер'

    date = fields.Date(string='Дата', tracking=True, required=True)
    type = fields.Selection([('transfer', 'Перевод')], string='Тип перевод', tracking=True, required=True)
    partner_1_id = fields.Many2one('amanat.contragent', string='Партнер 1', tracking=True)
    partner_2_id = fields.Many2one('amanat.contragent', string='Партнер 2', tracking=True)
    wallet_1_id = fields.Many2one('amanat.wallet', string='Кошелек Плательщика партнера 1', tracking=True)
    wallet_2_id = fields.Many2one('amanat.wallet', string='Кошелек Плательщика партнера 2', tracking=True)
    payer_1_id = fields.Many2one('amanat.payer', string='Плательщика партнера 1', tracking=True)
    payer_2_id = fields.Many2one('amanat.payer', string='Плательщика партнера 2', tracking=True)
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
    commission = fields.Float(string='Комиссия', tracking=True)