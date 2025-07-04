from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class ReconciliationDateRangeWizard(models.TransientModel):
    _name = 'amanat.reconciliation.date.range.wizard'
    _description = 'Выбор диапазона дат для сверок'

    field_name = fields.Selection([
        # Основная дата
        ('date', 'Дата'),
        
        # Даты диапазонов
        ('range_reconciliation_date_1', 'Сверка Дата 1 (from Диапазон)'),
        ('range_reconciliation_date_2', 'Сверка Дата 2 (from Диапазон)'),
        ('compare_balance_date_1', 'Сравнение баланса дата 1 (from Диапазон)'),
        ('compare_balance_date_2', 'Сравнение баланса дата 2 (from Диапазон)'),
        ('range_date_start', 'Дата начало (from Диапазон)'),
        ('range_date_end', 'Дата конец (from Диапазон)'),
    ], string='Поле для фильтрации', default='date', required=True)
    
    quick_filter = fields.Selection([
        ('yesterday', 'Вчера'),
        ('last_week', 'Последнюю неделю'),
        ('last_month', 'В прошлом месяце'),
        ('last_3_months', 'Последние 3 месяца'),
        ('last_6_months', 'Последние 6 месяцев'),
        ('custom', 'Выбрать даты'),
    ], string='Быстрый выбор')
    
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
            self.date_from = today - relativedelta(months=3)
            self.date_to = today
        elif self.quick_filter == 'last_6_months':
            self.date_from = today - relativedelta(months=6)
            self.date_to = today

    def action_apply_filter(self):
        """Применяет фильтр и закрывает wizard"""
        self.ensure_one()
        
        # Создаем домен для фильтрации
        domain = []
        if self.date_from:
            domain.append((self.field_name, '>=', self.date_from))
        if self.date_to:
            domain.append((self.field_name, '<=', self.date_to))
        
        # Получаем текущий action из контекста
        action = self.env.context.get('action_id')
        if action:
            action = self.env['ir.actions.act_window'].browse(action).read()[0]
        else:
            # Если action не найден, создаем новый
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Сверки',
                'res_model': 'amanat.reconciliation',
                'view_mode': 'list,form',
                'target': 'current',
            }
        
        # Обновляем домен
        action['domain'] = domain
        
        # Добавляем информацию о фильтре в контекст для отображения
        action['context'] = action.get('context', {})
        if isinstance(action['context'], str):
            action['context'] = {}
        
        action['context'].update({
            'search_date_range_field': self.field_name,
            'search_date_range_from': self.date_from.strftime('%d.%m.%Y') if self.date_from else '',
            'search_date_range_to': self.date_to.strftime('%d.%m.%Y') if self.date_to else '',
        })
        
        return action 