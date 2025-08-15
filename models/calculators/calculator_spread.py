# -*- coding: utf-8 -*-
# models/calculators/calculator_spread.py
from odoo import models, fields, api
from datetime import date


class CalculatorSpreadWizard(models.Model):
    """Калькулятор спреда между юанем и долларом"""
    _name = 'amanat.calculator.spread.wizard'
    _description = 'Спред между юанем и долларом'
    _order = 'create_date desc'

    # Информационные поля
    name = fields.Char(string='Название расчета', compute='_compute_name', store=True)
    create_uid = fields.Many2one('res.users', string='Создал', readonly=True)
    create_date = fields.Datetime(string='Дата создания', readonly=True)

    # Основные поля
    date = fields.Date(string='Дата', default=fields.Date.context_today, required=True)
    
    # Входные параметры (курсы)
    cbr_usd_rub = fields.Float(string='CBR USD/RUB (today)', digits=(16, 4), required=True,
                               help='Курс доллара к рублю по ЦБ РФ на сегодня')
    cbr_cny_rub = fields.Float(string='CBR CNY/RUB (today)', digits=(16, 4), required=True,
                               help='Курс юаня к рублю по ЦБ РФ на сегодня')
    xe_usd_cny = fields.Float(string='XE USD/CNY (1$ -> ¥)', digits=(16, 10), required=True,
                              help='Курс доллара к юаню по XE.com')
    
    # Расчетные поля
    calculated_usd_rub = fields.Float(string='Рассчитанный USD/RUB через юань', digits=(16, 4),
                                     compute='_compute_spread', store=False, readonly=True,
                                     help='CBR CNY/RUB * XE USD/CNY')
    spread_absolute = fields.Float(string='Спред (разница)', digits=(16, 4),
                                  compute='_compute_spread', store=False, readonly=True,
                                  help='Разность между CBR USD/RUB и рассчитанным USD/RUB')
    
    # Дополнительные расчетные поля для анализа
    spread_percent = fields.Float(string='Спред (%)', digits=(16, 4),
                                 compute='_compute_spread', store=False, readonly=True,
                                 help='Спред в процентах от курса CBR USD/RUB')
    
    # Поле для ввода суммы операции (опционально)
    amount_usd = fields.Float(string='Сумма операции (USD)', digits=(16, 2), default=0.0,
                             help='Сумма в долларах для расчета прибыли')
    profit_rub = fields.Float(string='Прибыль от спреда (RUB)', digits=(16, 2),
                             compute='_compute_spread', store=False, readonly=True,
                             help='Прибыль от спреда при заданной сумме операции')
    
    # Информационные поля
    spread_direction = fields.Char(string='Направление спреда', compute='_compute_spread', 
                                  store=False, readonly=True,
                                  help='Показывает, какой курс выгоднее')

    @api.depends('cbr_usd_rub', 'cbr_cny_rub', 'xe_usd_cny', 'amount_usd', 'date')
    def _compute_spread(self):
        for rec in self:
            cbr_usd = rec.cbr_usd_rub or 0.0
            cbr_cny = rec.cbr_cny_rub or 0.0
            xe_usd_cny = rec.xe_usd_cny or 0.0
            amount_usd = rec.amount_usd or 0.0
            
            # Рассчитываем USD/RUB через юань: CBR CNY/RUB * XE USD/CNY
            rec.calculated_usd_rub = cbr_cny * xe_usd_cny
            
            # Спред по новой формуле: CBR(USD/RUB) - CBR(CNY/RUB) * XE
            rec.spread_absolute = cbr_usd - (cbr_cny * xe_usd_cny)
            
            # Спред в процентах от CBR USD/RUB (widget="percentage" умножит на 100 автоматически)
            rec.spread_percent = (rec.spread_absolute / cbr_usd) if cbr_usd else 0.0
            
            # Прибыль от спреда при заданной сумме операции
            rec.profit_rub = rec.spread_absolute * amount_usd
            
            # Направление спреда
            if rec.spread_absolute > 0:
                rec.spread_direction = 'CBR USD выгоднее (положительный спред)'
            elif rec.spread_absolute < 0:
                rec.spread_direction = 'Через юань выгоднее (отрицательный спред)'
            else:
                rec.spread_direction = 'Курсы равны'

    @api.depends('date')
    def _compute_name(self):
        for rec in self:
            dt = rec.date or fields.Date.context_today(rec)
            rec.name = f'Спред CNY-USD — {dt}'
    
    # Методы для дополнительной функциональности
    def action_refresh_rates(self):
        """Обновить курсы валют (заглушка для будущей интеграции с API)"""
        for rec in self:
            # Здесь можно добавить интеграцию с CBR API и XE API
            pass
    
    def action_export_to_excel(self):
        """Экспорт расчетов в Excel"""
        for rec in self:
            # Здесь можно добавить экспорт в Excel
            pass
