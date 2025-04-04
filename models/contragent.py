# models/contragent.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Contragent(models.Model, AmanatBaseModel):
    _name = 'amanat.contragent'
    _description = 'Контрагент'
    _inherit = ["mail.thread", "mail.activity.mixin"]  

    name = fields.Char(string='Имя', required=True, tracking=True)
    recon_Balance_0 = fields.Char(string='Баланс RUB сверка', tracking=True)
    recon_Balance_1 = fields.Char(string='Баланс RUB сверка баланс 1', tracking=True)
    recon_Balance_2 = fields.Float(string='Баланс RUB сверка баланс 2', tracking=True)
    recon_cash_rub = fields.Float(string='Баланс RUB сверка КЕШ', tracking=True)
    recon_usdt = fields.Float(string='Баланс USDT сверка', tracking=True)
    recon_usd = fields.Float(string='Баланс USD сверка', tracking=True)
    recon_cash_usd = fields.Float(string='Баланс USD сверка КЕШ', tracking=True)
    recon_euro = fields.Float(string='Баланс EURO сверка', tracking=True)
    recon_cash_euro = fields.Float(string='Баланс EURO сверка КЕШ', tracking=True)
    recon_cny = fields.Float(string='Баланс CNY сверка', tracking=True)
    recon_cash_cny = fields.Float(string='Баланс CNY сверка КЕШ', tracking=True)
    recon_aed = fields.Float(string='Баланс AED сверка', tracking=True)
    recon_cash_aed = fields.Float(string='Баланс AED сверка КЕШ', tracking=True)
    recon_eq_dollar = fields.Float(string='Баланс Эквивалент $', tracking=True)
    recon_eq_compare_1 = fields.Float(string='Баланс Эквивалент $ сравнение 1', tracking=True)
    recon_eq_compare_2 = fields.Float(string='Баланс Эквивалент $ сравнение 2', tracking=True)

    cont_rub = fields.Float(string='Баланс RUB конт', tracking=True)
    cont_usd = fields.Float(string='Баланс USD конт', tracking=True)
    cont_usdt = fields.Float(string='Баланс USDT конт', tracking=True)
    cont_aed = fields.Float(string='Баланс AED конт', tracking=True)
    cont_euro = fields.Float(string='Баланс EURO конт', tracking=True)
    cont_cny = fields.Float(string='Баланс CNY конт', tracking=True)
    cash_cny = fields.Float(string='Баланс CNY КЕШ', tracking=True)
    cash_aed = fields.Float(string='Баланс AED КЕШ', tracking=True)
    cash_rub = fields.Float(string='Баланс RUB КЕШ', tracking=True)
    cash_euro = fields.Float(string='Баланс EURO КЕШ', tracking=True)
    cash_usd = fields.Float(string='Баланс USD КЕШ', tracking=True)

    payer_id = fields.Many2one('amanat.payer', string='Плательщики', required=False, tracking=True, ondelete='set null')
    payer_inn = fields.Char(string='ИНН (from Плательщики)', tracking=True, related='payer_id.inn', store=True)
    inn = fields.Char(string='ИНН', tracking=True)
    date_start = fields.Date(string='дата начало', tracking=True)
    date_end = fields.Date(string='дата конец', tracking=True)

   