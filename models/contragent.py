# models/contragent.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Contragent(models.Model, AmanatBaseModel):
    _name = 'amanat.contragent'
    _description = 'Контрагент'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]  

    name = fields.Char(string='Имя', required=True, tracking=True)
    recon_Balance_0 = fields.Float(string='Баланс RUB сверка', tracking=True)
    recon_Balance_1 = fields.Float(string='Баланс RUB сверка баланс 1', tracking=True)
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

    # Связь многие ко многим с Плательщиками
    payer_ids = fields.Many2many(
        'amanat.payer',
        'amanat_payer_contragent_rel',  # Общее имя таблицы-связи с моделью Payer
        'contragent_id',  # Поле-ссылка на эту модель
        'payer_id',  # Поле-ссылка на модель Плательщик
        string='Плательщики',
        tracking=True,
        ondelete='cascade'
    )
    payer_inn = fields.Char(
        string='ИНН (от Плательщиков)',
        compute='_compute_payer_inn',
        store=True,
        tracking=True
    )
    inn = fields.Char(string='ИНН', tracking=True)
    date_start = fields.Date(string='дата начало', tracking=True)
    date_end = fields.Date(string='дата конец', tracking=True)

    @api.depends('payer_ids.inn')
    def _compute_payer_inn(self):
        for record in self:
            # Фильтруем связанные записи, чтобы исключить несуществующие или пустые ИНН
            valid_payers = record.payer_ids.filtered(lambda r: r.exists() and r.inn)
            record.payer_inn = ", ".join(valid_payers.mapped('inn')) if valid_payers else ''

   