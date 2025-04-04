# models/wallet.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Wallet(models.Model, AmanatBaseModel):
    _name = 'amanat.wallet'
    _description = 'Кошелек плательщика'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Наименование', required=True, tracking=True)
    sum = fields.Float(string='Баланс деняг', default=0.0, tracking=True)


    partner_id = fields.Many2one('res.partner', string='Партнер', tracking=True)
    payer_id = fields.Many2one('amanat.payer', string='Плательщик', tracking=True)
    orders = fields.Float(string='Ордеры', tracking=True)
    money = fields.Float(string='Деньги', tracking=True)
    orders_copy = fields.Float(string='Ордеры copy', tracking=True)
    reserve_1 = fields.Float(string='Валютный резерв 1', tracking=True)
    reserve_2 = fields.Float(string='Валютный резерв 2', tracking=True)
    transfer_1 = fields.Float(string='Перевод', tracking=True)
    recon = fields.Float(string='Сверка', tracking=True)
    transfer_2 = fields.Float(string='Перевод 2', tracking=True)
    transfer_3 = fields.Float(string='Перевод 3', tracking=True)
    write_offs = fields.Float(string='Списания', tracking=True)
    partner_gold = fields.Float(string='Партнеры золото', tracking=True)
    bank_match = fields.Float(string='Выписка разнос', tracking=True) 