from odoo import models, fields
from .base_model import AmanatBaseModel

class Payer(models.Model, AmanatBaseModel):
    _name = 'amanat.payer'
    _description = 'Плательщик'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Наименование', required=True, tracking=True)
    contragent_id = fields.Many2one(
        'amanat.contragent',
        string='Контрагент',
        required=True,
        tracking=True
    )
    inn = fields.Char(string='ИНН', tracking=True)
    
    # Новые поля:
    contragents_ids = fields.Many2many(
        'amanat.contragent',
        string='КонтрАгенты',
        tracking=True
    )
    order_ids = fields.Many2many(
        'amanat.order',
        string='Ордеры',
        tracking=True
    )
    reconciliation = fields.Char(string='Сверка', tracking=True)
    transfer = fields.Char(string='Перевод', tracking=True)
    currency_reserve = fields.Char(string='Валютный резерв', tracking=True)
    conversion = fields.Char(string='Конвертация', tracking=True)
    investment = fields.Char(string='Инвестиция', tracking=True)
    gold_partners = fields.Many2many(
        'res.partner',
        string='Партнеры золото',
        tracking=True
    )
    deductions = fields.Char(string='Списания', tracking=True)
    applications = fields.Char(string='Заявки', tracking=True)
    pricelist_conduct = fields.Char(string='Прайс лист Плательщика За проведение', tracking=True)
    pricelist_profit = fields.Char(string='Прайс лист Плательщика Прибыль', tracking=True)
