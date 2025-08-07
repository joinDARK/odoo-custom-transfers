# models/price_list_royalty.py
from odoo import models, fields, api, exceptions
from .base_model import AmanatBaseModel

class PriceListRoyalty(models.Model, AmanatBaseModel):
    _name = 'amanat.price_list_royalty'
    _inherit = ['amanat.base.model']
    _description = 'Прайс лист роялти'

    # 1. наименование
    name = fields.Char(string="Наименование", required=True)
    
    # 2. контрагент связь с моделью контрагентов
    contragent_id = fields.Many2one(
        'amanat.contragent',
        string='Контрагент',
        required=False
    )
    
    # 3. отправитель или получатель или отправитель и получатель одновременно (single select)
    participant_type = fields.Selection([
        ('sender', 'Отправитель'),
        ('recipient', 'Получатель'),
        ('both', 'Отправитель или получатель')
    ], string="Тип участника", required=False)
    
    # 4. процент роялти
    royalty_percentage = fields.Float(
        string="Процент роялти (%)",
        required=False,
        digits=(16, 4),
        help="Введите значение в десятичном формате: 0.05 = 5%, 0.10 = 10%"
    )
    
    # 5. получатель роялти (связь с контрагентом)
    royalty_recipient_id = fields.Many2one(
        'amanat.contragent',
        string='Получатель роялти',
        required=False
    )
    
    # 6. тип операции (select перевод, конвертации, валютный резерв и инвестиции)
    operation_type = fields.Selection([
        ('transfer', 'Перевод'),
        ('conversion', 'Конвертации'),
        ('currency_reserve', 'Валютный резерв'),
        ('investment', 'Инвестиции')
    ], string="Тип операции", required=False)
    
    # 7. Даты диапазона
    date_from = fields.Date(string="Дата с", required=False)
    date_to = fields.Date(string="Дата по", required=False)

    # Валидация для процента роялти (виджет percentage работает с десятичными дробями)
    @api.constrains('royalty_percentage')
    def _check_royalty_percentage(self):
        for record in self:
            if record.royalty_percentage and (record.royalty_percentage < 0 or record.royalty_percentage > 1):
                raise exceptions.ValidationError("Процент роялти должен быть от 0% до 100% (значение от 0.0 до 1.0)")
    
    # Валидация для диапазона дат
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise exceptions.ValidationError("Дата 'с' не может быть больше даты 'по'")
