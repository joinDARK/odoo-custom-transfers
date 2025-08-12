# models/calculators/calculator_fixed_fee.py
from odoo import models, fields, api


class CalculatorFixedFeeWizard(models.Model):
    """Калькулятор фиксированного вознаграждения"""
    _name = 'amanat.calculator.fixed.fee.wizard'
    _description = 'Калькулятор фиксированного вознаграждения'
    _order = 'create_date desc'

    # Информационные поля
    name = fields.Char(string='Название расчета', compute='_compute_name', store=True)
    create_uid = fields.Many2one('res.users', string='Создал')
    create_date = fields.Datetime(string='Дата создания')

    # Основные поля
    date = fields.Date(string='Дата', default=fields.Date.today, required=True)
    
    # Реальный
    real_currency = fields.Selection([
        ('usd', 'USD'),
        ('eur', 'EUR'),
        ('rub', 'RUB'),
        ('kzt', 'KZT'),
        ('cny', 'CNY'),
    ], string='Валюта реальный', default='usd')
    real_amount = fields.Float(string='Сумма реальный', digits=(16, 4))
    real_cb_rate = fields.Float(string='Курс ЦБ реальный', digits=(16, 4))
    real_rub_amount = fields.Float(
        string='Сумма руб реальный', 
        compute='_compute_real_fields', 
        store=True, 
        digits=(16, 4)
    )
    general_percent_rate = fields.Float(string='Общий %', digits=(16, 4))
    general_percent_amount = fields.Float(
        string='Общий % (сумма)', 
        compute='_compute_real_fields', 
        store=True, 
        digits=(16, 4)
    )
    real_rub_total = fields.Float(
        string='Сумма руб итог реальный', 
        compute='_compute_real_fields', 
        store=True, 
        digits=(16, 4)
    )
    our_percent_rate = fields.Float(string='Наш %', digits=(16, 4))
    our_percent_amount = fields.Float(
        string='Наш % (сумма)', 
        compute='_compute_real_fields', 
        store=True, 
        digits=(16, 4)
    )
    
    # Клиенту
    client_currency = fields.Selection([
        ('usd', 'USD'),
        ('eur', 'EUR'),
        ('rub', 'RUB'),
        ('kzt', 'KZT'),
        ('cny', 'CNY'),
    ], string='Валюта клиент', default='usd')
    client_amount = fields.Float(string='Сумма клиент', digits=(16, 4))
    client_total_rate = fields.Float(string='Курс итог реальный', digits=(16, 4))
    client_rub_amount = fields.Float(
        string='Сумма руб клиенту', 
        compute='_compute_client_fields', 
        store=True, 
        digits=(16, 4)
    )
    client_percent_amount = fields.Float(string='Вознаграждение руб', digits=(16, 4))
    client_rub_total = fields.Float(
        string='Сумма руб итог клиенту', 
        compute='_compute_client_fields', 
        store=True, 
        digits=(16, 4)
    )
    
    # Итого
    reward_difference = fields.Float(
        string='Разница между вознагр', 
        compute='_compute_totals', 
        store=True, 
        digits=(16, 4)
    )
    add_to_payment = fields.Float(
        string='Добавить её к телу платежа', 
        compute='_compute_totals', 
        store=True, 
        digits=(16, 4)
    )
    final_rate = fields.Float(
        string='Итоговый курс', 
        compute='_compute_totals', 
        store=True, 
        digits=(16, 4)
    )
    embed_percent = fields.Float(
        string='Зашиваем %', 
        compute='_compute_totals', 
        store=True, 
        digits=(16, 4)
    )
    
    @api.depends('date', 'real_currency', 'client_currency')
    def _compute_name(self):
        for record in self:
            if record.date:
                date_str = record.date.strftime('%d.%m.%Y')
                record.name = f'Фикс. вознаграждение от {date_str}'
            else:
                record.name = 'Фикс. вознаграждение'

    @api.depends('real_amount', 'real_cb_rate', 'general_percent_rate', 'our_percent_rate')
    def _compute_real_fields(self):
        for record in self:
            # Сумма руб реальный = "Сумма реальный" * "Курс ЦБ реальный"
            if record.real_amount and record.real_cb_rate:
                record.real_rub_amount = record.real_amount * record.real_cb_rate
            else:
                record.real_rub_amount = 0
            
            # Общий % (сумма) = "Сумма руб реальный" * "Общий %"
            if record.real_rub_amount and record.general_percent_rate:
                record.general_percent_amount = record.real_rub_amount * (record.general_percent_rate / 100)
            else:
                record.general_percent_amount = 0
                
            # Сумма руб итог реальный = "Сумма руб реальный" + "Общий %"
            record.real_rub_total = record.real_rub_amount + record.general_percent_amount
            
            # Наш % (сумма) = "Сумма руб реальный" * "Наш %"
            if record.real_rub_amount and record.our_percent_rate:
                record.our_percent_amount = record.real_rub_amount * (record.our_percent_rate / 100)
            else:
                record.our_percent_amount = 0

    @api.depends('client_amount', 'client_total_rate', 'client_percent_amount')
    def _compute_client_fields(self):
        for record in self:
            # Сумма руб клиенту = "Сумма клиент" * "Курс итог реальный"
            if record.client_amount and record.client_total_rate:
                record.client_rub_amount = record.client_amount * record.client_total_rate
            else:
                record.client_rub_amount = 0
                
            # Сумма руб итог клиенту = "Сумма руб клиенту" + "Процент"
            record.client_rub_total = record.client_rub_amount + record.client_percent_amount

    @api.depends('general_percent_amount', 'client_percent_amount', 'real_rub_amount', 'real_amount')
    def _compute_totals(self):
        for record in self:
            # Разница между вознагр = "Общий %" - "Процент"
            record.reward_difference = record.general_percent_amount - record.client_percent_amount
            
            # Добавить её к телу платежа = "Сумма руб реальный" + "Разница между вознагр"
            record.add_to_payment = record.real_rub_amount + record.reward_difference
            
            # Итоговый курс = "Добавить её к телу платежа" / "Сумма реальный"
            if record.real_amount and record.add_to_payment:
                record.final_rate = record.add_to_payment / record.real_amount
            else:
                record.final_rate = 0
                
            # Зашиваем % = "Разница между вознагр" / "Сумма руб реальный"
            if record.real_rub_amount and record.reward_difference:
                record.embed_percent = (record.reward_difference / record.real_rub_amount) * 100
            else:
                record.embed_percent = 0

 