# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date, timedelta
import logging
from odoo.tools import ormcache

_logger = logging.getLogger(__name__)

class ZayavkaFiksDashboard(models.Model):
    _name = 'amanat.zayavka_fiks_dashboard'
    _description = 'Дашборд Фикс Заявки'
    
    name = fields.Char(string='Название', default='Дашборд Фикс Заявки')
    
    def init(self):
        """Создание индексов для оптимизации"""
        super().init()
        # Создаем индекс для поля rate_fixation_date если его нет
        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_amanat_zayavka_rate_fixation_date 
            ON amanat_zayavka (rate_fixation_date)
        """)
        # Создаем составной индекс для оптимизации запросов по валютам и датам
        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_amanat_zayavka_currency_date 
            ON amanat_zayavka (currency, rate_fixation_date)
        """)
        _logger.info("Индексы для оптимизации дашборда фикс заявок созданы")
    
    @api.model
    def get_fiks_dashboard_data(self, date_from=None, date_to=None):
        """
        Получение данных для дашборда фикс заявок в диапазоне дат
        """
        try:
            _logger.info(f"Получение данных дашборда. date_from: {date_from}, date_to: {date_to}")
            
            # Если даты не указаны или пустые строки - показываем все заявки
            domain = []
            
            if date_from and date_from.strip():
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                domain.append(('rate_fixation_date', '>=', date_from))
            else:
                date_from = None
                
            if date_to and date_to.strip():
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                domain.append(('rate_fixation_date', '<=', date_to))
            else:
                date_to = None
            
            # Получаем оптимизированные данные с кэшированием
            data = self._get_cached_dashboard_metrics(
                str(domain),  # Кэш по домену как строке
                date_from.strftime('%Y-%m-%d') if date_from else '',
                date_to.strftime('%Y-%m-%d') if date_to else ''
            )
            
            return {
                'success': True,
                'data': data
            }
            
        except Exception as e:
            _logger.error(f"Ошибка получения данных дашборда фикс заявок: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @ormcache('domain_str', 'date_from_str', 'date_to_str')
    def _get_cached_dashboard_metrics(self, domain_str, date_from_str, date_to_str):
        """
        Кэшированный метод получения метрик дашборда
        """
        # Восстанавливаем домен из строки
        domain = eval(domain_str) if domain_str != "[]" else []
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
        
        _logger.info(f"Вычисление метрик для домена: {domain}")
        
        # Получаем агрегированные данные одним запросом
        period_data = self._get_aggregated_data(domain)
        
        # Получаем данные за сегодня
        today_data = self._get_today_aggregated_data()
        
        return {
            'date_from': date_from_str,
            'date_to': date_to_str,
            **period_data,
            'today_data': today_data
        }
    
    def _get_aggregated_data(self, domain):
        """
        Получение агрегированных данных за период используя SQL
        """
        try:
            # Группируем по валютам и получаем суммы и средние курсы
            currency_groups = self.env['amanat.zayavka'].read_group(
                domain + [('currency', '!=', False)],
                ['currency', 'amount:sum', 'effective_rate:avg'],
                ['currency']
            )
            
            _logger.info(f"Получено {len(currency_groups)} групп валют")
            
            # Инициализируем результаты
            currency_sums = {'usd': 0, 'cny': 0, 'euro': 0, 'aed': 0, 'usdt': 0}
            average_rates = {'usd': "0", 'cny': "0", 'euro': "0", 'aed': "0", 'usdt': "0"}
            
            # Общее количество заявок
            total_count = self.env['amanat.zayavka'].search_count(domain)
            
            # Обрабатываем группы валют
            for group in currency_groups:
                currency = group['currency']
                amount_sum = group['amount'] or 0
                rate_avg = group['effective_rate'] or 0
                
                # Маппинг валют (включая кэш варианты)
                if currency in ['usd', 'usd_cashe']:
                    currency_sums['usd'] += amount_sum
                    if rate_avg > 0:
                        average_rates['usd'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency in ['cny', 'cny_cashe']:
                    currency_sums['cny'] += amount_sum
                    if rate_avg > 0:
                        average_rates['cny'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency in ['euro', 'euro_cashe']:
                    currency_sums['euro'] += amount_sum
                    if rate_avg > 0:
                        average_rates['euro'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency in ['aed', 'aed_cashe']:
                    currency_sums['aed'] += amount_sum
                    if rate_avg > 0:
                        average_rates['aed'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency in ['usdt', 'usdt_cashe']:
                    currency_sums['usdt'] += amount_sum
                    if rate_avg > 0:
                        average_rates['usdt'] = f"{rate_avg:,.4f}".replace('.', ',')
            
            # Вычисляем эквиваленты в долларах
            usd_equivalents = self._calculate_usd_equivalents_optimized(currency_sums)
            
            # Данные для графика
            chart_data = self._prepare_chart_data(currency_sums)
            
            _logger.info(f"Агрегированные данные: заявок={total_count}, USD={currency_sums['usd']}, CNY={currency_sums['cny']}")
            
            return {
                'average_rates': average_rates,
                'total_count': total_count,
                'equivalent_usd': f"{usd_equivalents['total']:,.2f}",
                'cny_equivalent_usd': f"{usd_equivalents['cny']:,.2f}",
                'euro_equivalent_usd': f"{usd_equivalents['euro']:,.2f}",
                'usd_sum': f"{currency_sums['usd']:,.0f}",
                'cny_sum': f"{currency_sums['cny']:,.0f}",
                'euro_sum': f"{currency_sums['euro']:,.0f}",
                'aed_sum': f"{currency_sums['aed']:,.0f}",
                'usdt_sum': f"{currency_sums['usdt']:,.0f}",
                'chart_data': chart_data
            }
                
        except Exception as e:
            _logger.error(f"Ошибка получения агрегированных данных: {e}")
            return self._get_empty_metrics()
    
    def _get_today_aggregated_data(self):
        """
        Получение агрегированных данных за сегодня
        """
        try:
            today = date.today()
            domain = [('rate_fixation_date', '=', today)]
            
            # Используем тот же метод агрегации
            today_metrics = self._get_aggregated_data(domain)
            
            # Данные для графика за сегодня
            currency_sums = {
                'usd': float(today_metrics['usd_sum'].replace(',', '')),
                'cny': float(today_metrics['cny_sum'].replace(',', '')),
                'euro': float(today_metrics['euro_sum'].replace(',', '')),
                'aed': float(today_metrics['aed_sum'].replace(',', '')),
                'usdt': float(today_metrics['usdt_sum'].replace(',', ''))
            }
            
            today_chart_data = self._prepare_today_chart_data(currency_sums)
            today_metrics['chart_data'] = today_chart_data
            
            _logger.info(f"Данные за сегодня: заявок={today_metrics['total_count']}")
            
            return today_metrics
            
        except Exception as e:
            _logger.error(f"Ошибка получения данных за сегодня: {e}")
            return self._get_empty_metrics()
    
    def _calculate_usd_equivalents_optimized(self, currency_sums):
        """
        Оптимизированный подсчет эквивалентов в долларах
        """
        try:
            # Используем фиксированные курсы для быстрого расчета
            cny_to_usd = currency_sums['cny'] / 7.2  # Примерный курс CNY к USD
            euro_to_usd = currency_sums['euro'] * 1.1  # Примерный курс EUR к USD
            aed_to_usd = currency_sums['aed'] / 3.67  # Примерный курс AED к USD
            
            total_usd = currency_sums['usd'] + cny_to_usd + euro_to_usd + aed_to_usd
            # USDT не включается в эквивалент USD
            
            return {
                'total': total_usd,
                'cny': cny_to_usd,
                'euro': euro_to_usd
            }
        except Exception as e:
            _logger.error(f"Ошибка подсчета эквивалентов в долларах: {e}")
            return {'total': 0, 'cny': 0, 'euro': 0}
    
    def _prepare_chart_data(self, currency_sums):
        """
        Подготовка данных для графика
        """
        try:
            return {
                'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT'],
                'datasets': [{
                    'label': 'Сумма по валютам',
                    'data': [
                        currency_sums['usd'],
                        currency_sums['cny'],
                        currency_sums['euro'],
                        currency_sums['aed'],
                        currency_sums['usdt']
                    ],
                    'backgroundColor': [
                        '#5b9bd5',  # USD - голубой
                        '#70ad47',  # CNY - зеленый  
                        '#ffc000',  # EURO - желтый
                        '#7030a0',  # AED - фиолетовый
                        '#ff6b35'   # USDT - оранжевый
                    ],
                    'borderColor': [
                        '#4472c4',
                        '#548235',
                        '#d99694',
                        '#5b2c87',
                        '#e85a2b'
                    ],
                    'borderWidth': 1,
                    'borderRadius': 4,
                    'borderSkipped': False
                }]
            }
        except Exception as e:
            _logger.error(f"Ошибка подготовки данных для графика: {e}")
            return self._get_empty_chart_data()
    
    def _prepare_today_chart_data(self, currency_sums):
        """
        Подготовка данных для графика за сегодня
        """
        try:
            return {
                'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT'],
                'datasets': [{
                    'label': 'Сумма по валютам сегодня',
                    'data': [
                        currency_sums['usd'],
                        currency_sums['cny'],
                        currency_sums['euro'],
                        currency_sums['aed'],
                        currency_sums['usdt']
                    ],
                    'backgroundColor': [
                        '#5b9bd5',  # USD - голубой
                        '#70ad47',  # CNY - зеленый  
                        '#ffc000',  # EURO - желтый
                        '#7030a0',  # AED - фиолетовый
                        '#ff6b35'   # USDT - оранжевый
                    ],
                    'borderColor': [
                        '#4472c4',
                        '#548235',
                        '#d99694',
                        '#5b2c87',
                        '#e85a2b'
                    ],
                    'borderWidth': 1,
                    'borderRadius': 4,
                    'borderSkipped': False
                }]
            }
        except Exception as e:
            _logger.error(f"Ошибка подготовки данных для графика за сегодня: {e}")
            return self._get_empty_chart_data()
    
    def _get_empty_metrics(self):
        """
        Возвращает пустые метрики при ошибках
        """
        return {
            'average_rates': {
                'usd': "0",
                'cny': "0",
                'euro': "0",
                'aed': "0",
                'usdt': "0"
            },
            'total_count': 0,
            'equivalent_usd': "0,00",
            'cny_equivalent_usd': "0,00",
            'euro_equivalent_usd': "0,00",
            'usd_sum': "0",
            'cny_sum': "0",
            'euro_sum': "0",
            'aed_sum': "0",
            'usdt_sum': "0",
            'chart_data': self._get_empty_chart_data()
        }
    
    def _get_empty_chart_data(self):
        """
        Возвращает пустые данные для графика
        """
        return {
            'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT'],
            'datasets': [{
                'label': 'Сумма по валютам',
                'data': [0, 0, 0, 0, 0],
                'backgroundColor': ['#5b9bd5', '#70ad47', '#ffc000', '#7030a0', '#ff6b35']
            }]
        } 
    
 