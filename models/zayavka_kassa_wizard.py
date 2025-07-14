from odoo import models, fields, api
from datetime import datetime, timedelta


class ZayavkaKassaWizard(models.TransientModel):
    _name = 'amanat.zayavka.kassa.wizard'
    _description = 'Выбор кассы и диапазона дат для заявок'

    kassa_type = fields.Selection([
        ('kassa_ivan', 'Касса Иван'),
        ('kassa_2', 'Касса 2'),
        ('kassa_3', 'Касса 3'),
        ('all', 'Все кассы'),
    ], string='Касса', default='all', required=True)
    
    field_name = fields.Selection([
        # Основные даты
        ('date_placement', 'Дата размещения'),
        ('taken_in_work_date', 'Взята в работу'),
        ('instruction_signed_date', 'Подписано поручение'),
        ('rate_fixation_date', 'Дата фиксации курса'),
        
        # Даты инвойса и договоров
        ('invoice_date', 'Выставлен инвойс'),
        ('agent_contract_date', 'Подписан агент./субагент. договор'),
        ('bank_registration_date', 'Поставлен на учет в банке'),
        
        # Даты оплаты
        ('payment_date', 'Передано в оплату / оплачена валюта'),
        ('supplier_currency_paid_date', 'Оплачена валюта поставщику/субагенту'),
        ('supplier_currency_received_date', 'Получена валюта поставщиком/субагентом'),
        ('client_ruble_paid_date', 'Оплачен рубль клиенту (экспорт)'),
        
        # Даты аккредитива
        ('accreditive_open_date', 'Открыт аккредитив'),
        ('accreditive_revealed_date', 'Аккредитив раскрыт'),
        
        # Даты SWIFT
        ('swift_received_date', 'Получен SWIFT'),
        ('swift_103_requested_date', 'Запросили SWIFT 103'),
        ('swift_199_requested_date', 'Запросили SWIFT 199'),
        ('swift_103_received_date', 'Получили SWIFT 103'),
        ('swift_199_received_date', 'Получили SWIFT 199'),
        
        # Даты возврата
        ('return_requested_date', 'Возврат запрошен'),
        ('return_money_received_date', 'Деньги по возврату получены'),
        
        # Даты закрытия сделки
        ('act_report_signed_date', 'Подписан акт-отчет'),
        ('deal_closed_date', 'Сделка закрыта'),
        
        # Даты субагента
        ('subagent_docs_prepared_date', 'Подготовлены документы между агентом и субагентом'),
        
        # Даты поступления на РС
        ('date_received_on_pc12', 'Дата поступления на PC12'),
        ('date_agent_on_pc', 'Дата агентского на PC'),
        ('date_received_on_pc_payment', 'Дата поступления на РС расчет'),
        ('date_received_tezera', 'Дата поступления ТЕЗЕРА'),
        
        # Даты диапазонов и периодов
        ('period_date_1', 'Дата 1 (from Период)'),
        ('period_date_2', 'Дата 2 (from Период)'),
        ('range_date_start', 'Дата начало (from диапазон)'),
        ('range_date_end', 'Дата конец (from диапазон)'),
        ('range_date_start_copy', 'Дата начало copy (from диапазон)'),
        ('range_date_end_copy', 'Дата конец copy (from диапазон)'),
        
        # Даты Совкомбанка
        ('assignment_signed_sovcom', 'Подписано поручение (для Совкомбанка)'),
    ], string='Поле для фильтрации по дате', default='date_placement', required=True)
    
    quick_filter = fields.Selection([
        ('yesterday', 'Вчера'),
        ('last_week', 'Последнюю неделю'),
        ('last_month', 'В прошлом месяце'),
        ('last_3_months', 'Последние 3 месяца'),
        ('last_6_months', 'Последние 6 месяцев'),
        ('custom', 'Выбрать даты'),
    ], string='Быстрый выбор периода')
    
    date_from = fields.Date(string='Дата начала')
    date_to = fields.Date(string='Дата конец')

    @api.onchange('quick_filter')
    def _onchange_quick_filter(self):
        """Автоматически устанавливает даты при выборе быстрого фильтра"""
        if not self.quick_filter or self.quick_filter == 'custom':
            return
            
        today = fields.Date.today()
        
        if self.quick_filter == 'yesterday':
            self.date_from = today - timedelta(days=1)
            self.date_to = today - timedelta(days=1)
        elif self.quick_filter == 'last_week':
            self.date_from = today - timedelta(days=7)
            self.date_to = today
        elif self.quick_filter == 'last_month':
            # Первый день прошлого месяца
            first_day_current_month = today.replace(day=1)
            last_day_previous_month = first_day_current_month - timedelta(days=1)
            first_day_previous_month = last_day_previous_month.replace(day=1)
            self.date_from = first_day_previous_month
            self.date_to = last_day_previous_month
        elif self.quick_filter == 'last_3_months':
            self.date_from = today - timedelta(days=90)
            self.date_to = today
        elif self.quick_filter == 'last_6_months':
            self.date_from = today - timedelta(days=180)
            self.date_to = today

    def action_apply_filter(self):
        """Применяет фильтр к заявкам"""
        domain = []
        
        # Фильтр по дате
        if self.date_from and self.date_to:
            if self.field_name:
                domain.extend([
                    (self.field_name, '>=', self.date_from),
                    (self.field_name, '<=', self.date_to)
                ])
        elif self.date_from:
            domain.append((self.field_name, '>=', self.date_from))
        elif self.date_to:
            domain.append((self.field_name, '<=', self.date_to))
        
        # Фильтр по кассе
        if self.kassa_type and self.kassa_type != 'all':
            # Получаем контрагентов из выбранной кассы
            if self.kassa_type == 'kassa_ivan':
                kassa_records = self.env['amanat.kassa_ivan'].search([])
            elif self.kassa_type == 'kassa_2':
                kassa_records = self.env['amanat.kassa_2'].search([])
            elif self.kassa_type == 'kassa_3':
                kassa_records = self.env['amanat.kassa_3'].search([])
            
            if kassa_records:
                contragent_ids = kassa_records.mapped('contragent_id.id')
                domain.append(('contragent_id', 'in', contragent_ids))
            else:
                # Если в кассе нет записей, возвращаем пустой результат
                domain.append(('id', '=', False))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Заявки - Касса: {dict(self._fields["kassa_type"].selection)[self.kassa_type]}',
            'res_model': 'amanat.zayavka',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'main',
            'context': self.env.context,
        } 