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
            # Фильтры для исключения кэш валют
            exclude_currencies = [
                'aed_cashe', 'cny_cashe', 'euro_cashe', 
                'rub_cashe', 'thb_cashe', 'usd_cashe', 'usdt_cashe'
            ]
            
            # Группируем по валютам и получаем суммы и средние курсы с применением всех фильтров
            currency_groups = self.env['amanat.zayavka'].read_group(
                domain + [
                    ('currency', '!=', False), 
                    ('hidden_hadge', '=', False),
                    ('currency', 'not in', exclude_currencies),
                    ('prefix', '=', False),
                    ('hide_in_dashboard', '!=', True),
                ],
                ['currency', 'amount:sum', 'effective_rate:avg'],
                ['currency']
            )
            
            _logger.info(f"Получено {len(currency_groups)} групп валют")
            
            # Инициализируем результаты
            currency_sums = {'usd': 0, 'cny': 0, 'euro': 0, 'aed': 0, 'usdt': 0, 'rub': 0, 'thb': 0}
            average_rates = {'usd': "0", 'cny': "0", 'euro': "0", 'aed': "0", 'usdt': "0", 'rub': "0", 'thb': "0"}
            
            # Общее количество заявок с применением всех фильтров
            total_count = self.env['amanat.zayavka'].search_count(
                domain + [
                    ('hidden_hadge', '=', False),
                    ('currency', 'not in', exclude_currencies),
                    ('prefix', '=', False),
                    ('hide_in_dashboard', '!=', True),
                ]
            )
            
            # Обрабатываем группы валют
            for group in currency_groups:
                currency = group['currency']
                amount_sum = group['amount'] or 0
                rate_avg = group['effective_rate'] or 0
                
                # Маппинг валют (исключая кэш варианты, которые уже отфильтрованы)
                if currency == 'usd':
                    currency_sums['usd'] += amount_sum
                    if rate_avg > 0:
                        average_rates['usd'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency == 'cny':
                    currency_sums['cny'] += amount_sum
                    if rate_avg > 0:
                        average_rates['cny'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency == 'euro':
                    currency_sums['euro'] += amount_sum
                    if rate_avg > 0:
                        average_rates['euro'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency == 'aed':
                    currency_sums['aed'] += amount_sum
                    if rate_avg > 0:
                        average_rates['aed'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency == 'usdt':
                    currency_sums['usdt'] += amount_sum
                    if rate_avg > 0:
                        average_rates['usdt'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency == 'rub':
                    currency_sums['rub'] += amount_sum
                    if rate_avg > 0:
                        average_rates['rub'] = f"{rate_avg:,.4f}".replace('.', ',')
                elif currency == 'thb':
                    currency_sums['thb'] += amount_sum
                    if rate_avg > 0:
                        average_rates['thb'] = f"{rate_avg:,.4f}".replace('.', ',')
            
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
                'rub_sum': f"{currency_sums['rub']:,.0f}",
                'thb_sum': f"{currency_sums['thb']:,.0f}",
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
            
            # Получаем список заявок за сегодня для таблицы
            today_orders = self._get_today_orders_list()
            today_metrics['orders_list'] = today_orders
            
            # Данные для графика за сегодня
            currency_sums = {
                'usd': float(today_metrics['usd_sum'].replace(',', '')),
                'cny': float(today_metrics['cny_sum'].replace(',', '')),
                'euro': float(today_metrics['euro_sum'].replace(',', '')),
                'aed': float(today_metrics['aed_sum'].replace(',', '')),
                'usdt': float(today_metrics['usdt_sum'].replace(',', '')),
                'rub': float(today_metrics['rub_sum'].replace(',', '')),
                'thb': float(today_metrics['thb_sum'].replace(',', ''))
            }
            
            today_chart_data = self._prepare_today_chart_data(currency_sums)
            today_metrics['chart_data'] = today_chart_data
            
            _logger.info(f"Данные за сегодня: заявок={today_metrics['total_count']}")
            
            return today_metrics
            
        except Exception as e:
            _logger.error(f"Ошибка получения данных за сегодня: {e}")
            return self._get_empty_metrics()
    
    def _get_today_orders_list(self):
        """
        Получение списка заявок за сегодня для отображения в таблице
        """
        try:
            today = date.today()
            domain = [('rate_fixation_date', '=', today)]
            
            # Фильтры для исключения кэш валют и других условий
            exclude_currencies = [
                'aed_cashe', 'cny_cashe', 'euro_cashe', 
                'rub_cashe', 'thb_cashe', 'usd_cashe', 'usdt_cashe'
            ]
            
            # Получаем заявки за сегодня с фильтрами, отсортированные по времени создания (новые сначала)
            orders = self.env['amanat.zayavka'].search(
                domain + [
                    ('hidden_hadge', '=', False),           # Скрытый хэдж = False
                    ('currency', 'not in', exclude_currencies), # Исключить кэш валюты
                    ('prefix', '=', False),                 # Перефикс = False
                    ('hide_in_dashboard', '!=', True),      # Не отображать в дашборде != True
                ], 
                order='create_date desc'
            )
            
            orders_list = []
            for order in orders:
                # Валюта - преобразуем техническое значение в читаемое
                currency_map = {
                    'usd': 'USD',
                    'cny': 'CNY',
                    'euro': 'EURO',
                    'aed': 'AED',
                    'usdt': 'USDT',
                    'rub': 'RUB',
                    'thb': 'THB',
                    'usd_cashe': 'USD КЭШ',
                    'cny_cashe': 'CNY КЭШ',
                    'euro_cashe': 'EURO КЭШ',
                    'aed_cashe': 'AED КЭШ',
                    'usdt_cashe': 'USDT КЭШ',
                    'rub_cashe': 'RUB КЭШ',
                    'thb_cashe': 'THB КЭШ',
                }
                currency_display = currency_map.get(order.currency, order.currency or 'Не указана')
                
                # Тип сделки
                deal_type_map = {
                    'import': 'Перевод',
                    'export': 'Экспорт', 
                    'import_export': 'Импорт-экспорт',
                    'export_import': 'Экспорт-импорт'
                }
                deal_type_display = deal_type_map.get(order.deal_type, order.deal_type or 'Перевод')
                
                # Статус с декорациями как в list view
                status_class = ''
                if order.status == '21':
                    status_class = 'table-success'  # decoration-success
                elif order.status == '22':
                    status_class = 'table-danger'   # decoration-danger

                # Маппинг статусов
                status_map = {
                    '1': '1. В работе',
                    '2': '2. Выставлен инвойс',
                    '3': '3. Зафиксирован курс',
                    '4': '4. Подписано поручение',
                    '5': '5. Готовим на оплату',
                    '6': '6. Передано на оплату',
                    '7': '7. Получили ПП',
                    '8': '8. Получили Swift',
                    '9': '9. Подписан Акт-отчет',
                    '10': '10. Ждем рубли',
                    '11': '11. Получили рубли',
                    '12': '12. Ждем поступление валюты',
                    '13': '13. Валюта у получателя',
                    '14': '14. Запрошен Swift 103',
                    '15': '15. Получен Swift 103',
                    '16': '16. Запрошен Swift 199',
                    '17': '17. Получен Swift 199',
                    '18': '18. Ожидаем возврат',
                    '19': '19. Оплачено повторно',
                    '20': '20. Возврат',
                    '21': '21. Заявка закрыта',
                    '22': '22. Отменено клиентом',
                    '23': '23. Согласован получатель (экспорт)',
                    '24': '24. Получили валюту (экспорт)',
                    '25': '25. Оплатили рубли (экспорт)',
                }

                # Маппинг условий оплаты
                payment_conditions_map = {
                    'prepayment': 'Предоплата',
                    'postpayment': 'Постоплата',
                    'deferred_payment': 'Отсрочка платежа',
                    'cash_on_delivery': 'Наложенный платеж',
                    'mixed': 'Смешанная',
                    'credit': 'Кредит',
                }

                orders_list.append({
                    'id': order.id,
                    'zayavka_num': order.zayavka_num or '',
                    'contragent_name': order.contragent_id.name if order.contragent_id else '',
                    'agent_name': ', '.join(order.manager_ids.mapped('name')) if order.manager_ids else '',
                    'amount': f"{order.amount:,.0f}".replace(',', ' ') if order.amount else "0",
                    'currency_display': currency_display,
                    'rate_field': f"{order.rate_field:,.4f}".replace('.', ',') if order.rate_field else "0,0000",
                    'payment_conditions_display': payment_conditions_map.get(order.payment_conditions, order.payment_conditions or ''),
                    'comment': order.comment or '',
                    'status_display': status_map.get(order.status, order.status or ''),
                    'status_class': status_class
                })
            
            _logger.info(f"Получено {len(orders_list)} заявок за сегодня")
            return orders_list
            
        except Exception as e:
            _logger.error(f"Ошибка получения списка заявок за сегодня: {e}")
            return []
    
    def _calculate_usd_equivalents_optimized(self, currency_sums):
        """
        Оптимизированный подсчет эквивалентов в долларах
        """
        try:
            # Используем фиксированные курсы для быстрого расчета
            cny_to_usd = currency_sums['cny'] / 7.2  # Примерный курс CNY к USD
            euro_to_usd = currency_sums['euro'] * 1.1  # Примерный курс EUR к USD
            aed_to_usd = currency_sums['aed'] / 3.67  # Примерный курс AED к USD
            rub_to_usd = currency_sums['rub'] / 92.0  # Примерный курс RUB к USD
            thb_to_usd = currency_sums['thb'] / 34.5  # Примерный курс THB к USD
            
            total_usd = currency_sums['usd'] + cny_to_usd + euro_to_usd + aed_to_usd + rub_to_usd + thb_to_usd
            # USDT не включается в эквивалент USD
            
            return {
                'total': total_usd,
                'cny': cny_to_usd,
                'euro': euro_to_usd,
                'rub': rub_to_usd,
                'thb': thb_to_usd
            }
        except Exception as e:
            _logger.error(f"Ошибка подсчета эквивалентов в долларах: {e}")
            return {'total': 0, 'cny': 0, 'euro': 0, 'rub': 0, 'thb': 0}
    
    def _prepare_chart_data(self, currency_sums):
        """
        Подготовка данных для графика
        """
        try:
            return {
                'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT', 'RUB', 'THB'],
                'datasets': [{
                    'label': 'Сумма по валютам',
                    'data': [
                        currency_sums['usd'],
                        currency_sums['cny'],
                        currency_sums['euro'],
                        currency_sums['aed'],
                        currency_sums['usdt'],
                        currency_sums['rub'],
                        currency_sums['thb']
                    ],
                    'backgroundColor': [
                        '#5b9bd5',  # USD - голубой
                        '#70ad47',  # CNY - зеленый  
                        '#ffc000',  # EURO - желтый
                        '#7030a0',  # AED - фиолетовый
                        '#ff6b35',  # USDT - оранжевый
                        '#c55a5a',  # RUB - красный
                        '#6fa8dc'   # THB - светло-синий
                    ],
                    'borderColor': [
                        '#4472c4',
                        '#548235',
                        '#d99694',
                        '#5b2c87',
                        '#e85a2b',
                        '#a64444',
                        '#5b8ab3'
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
                'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT', 'RUB', 'THB'],
                'datasets': [{
                    'label': 'Сумма по валютам сегодня',
                    'data': [
                        currency_sums['usd'],
                        currency_sums['cny'],
                        currency_sums['euro'],
                        currency_sums['aed'],
                        currency_sums['usdt'],
                        currency_sums['rub'],
                        currency_sums['thb']
                    ],
                    'backgroundColor': [
                        '#5b9bd5',  # USD - голубой
                        '#70ad47',  # CNY - зеленый  
                        '#ffc000',  # EURO - желтый
                        '#7030a0',  # AED - фиолетовый
                        '#ff6b35',  # USDT - оранжевый
                        '#c55a5a',  # RUB - красный
                        '#6fa8dc'   # THB - светло-синий
                    ],
                    'borderColor': [
                        '#4472c4',
                        '#548235',
                        '#d99694',
                        '#5b2c87',
                        '#e85a2b',
                        '#a64444',
                        '#5b8ab3'
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
                'usdt': "0",
                'rub': "0",
                'thb': "0"
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
            'rub_sum': "0",
            'thb_sum': "0",
            'chart_data': self._get_empty_chart_data()
        }
    
    def _get_empty_chart_data(self):
        """
        Возвращает пустые данные для графика
        """
        return {
            'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT', 'RUB', 'THB'],
            'datasets': [{
                'label': 'Сумма по валютам',
                'data': [0, 0, 0, 0, 0, 0, 0],
                'backgroundColor': ['#5b9bd5', '#70ad47', '#ffc000', '#7030a0', '#ff6b35', '#c55a5a', '#6fa8dc']
            }]
        }
    
    @api.model
    def invalidate_dashboard_cache(self):
        """
        Инвалидация кэша дашборда при изменении данных заявок
        """
        try:
            # Очищаем кэш метода _get_cached_dashboard_metrics
            self.env.registry.clear_cache()
            _logger.info("Кэш дашборда фикс заявок успешно очищен")
        except Exception as e:
            _logger.error(f"Ошибка очистки кэша дашборда фикс заявок: {e}")
    
 