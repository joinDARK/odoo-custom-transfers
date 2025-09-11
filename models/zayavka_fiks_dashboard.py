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
            
            # Если даты не указаны - ограничиваем по умолчанию последним годом для производительности
            domain = []
            
            if date_from and date_from.strip():
                try:
                    date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                    domain.append(('rate_fixation_date', '>=', date_from))
                except ValueError as e:
                    _logger.error(f"Некорректный формат date_from: {date_from}, ошибка: {e}")
                    date_from = None
            else:
                date_from = None
                
            if date_to and date_to.strip():
                try:
                    date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                    domain.append(('rate_fixation_date', '<=', date_to))
                except ValueError as e:
                    _logger.error(f"Некорректный формат date_to: {date_to}, ошибка: {e}")
                    date_to = None
            else:
                date_to = None
                
            # Если даты не указаны, ограничиваем последним годом для предотвращения перегрузки
            if not date_from and not date_to:
                one_year_ago = date.today() - timedelta(days=365)
                domain.append(('rate_fixation_date', '>=', one_year_ago))
                _logger.info(f"Применено ограничение по умолчанию: данные за последний год с {one_year_ago}")
                
            # Дополнительная проверка на разумный диапазон дат
            if date_from and date_to and (date_to - date_from).days > 1095:  # более 3 лет
                _logger.warning(f"Запрошен большой диапазон дат: {(date_to - date_from).days} дней")
                # Ограничиваем последними 3 годами
                date_from = date_to - timedelta(days=1095)
                domain = [d for d in domain if not (isinstance(d, tuple) and d[0] == 'rate_fixation_date' and d[1] == '>=')]
                domain.append(('rate_fixation_date', '>=', date_from))
                _logger.info(f"Диапазон ограничен до 3 лет: с {date_from} по {date_to}")
            
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
        try:
            # Безопасное восстановление домена из строки
            import ast
            domain = ast.literal_eval(domain_str) if domain_str != "[]" else []
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
        except (ValueError, SyntaxError, Exception) as e:
            _logger.error(f"Ошибка парсинга параметров кэша: {e}")
            domain = []
            date_from = None
            date_to = None
        
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
            # Проверяем существование модели заявки
            if 'amanat.zayavka' not in self.env:
                _logger.error("Модель amanat.zayavka не найдена")
                return self._get_empty_metrics()
            
            zayavka_model = self.env['amanat.zayavka']
            
            # Проверяем существование необходимых полей
            required_fields = ['currency', 'amount', 'hidden_rate', 'effective_rate', 'rate_field', 'hidden_hadge', 'prefix', 'hide_in_dashboard']
            model_fields = zayavka_model._fields.keys()
            
            missing_fields = [field for field in required_fields if field not in model_fields]
            if missing_fields:
                _logger.error(f"Отсутствуют поля в модели amanat.zayavka: {missing_fields}")
                
            # Используем доступные поля с приоритетом hidden_rate
            available_read_fields = ['currency']
            if 'amount' in model_fields:
                available_read_fields.append('amount:sum')
            
            # Приоритет курса: hidden_rate -> effective_rate -> rate_field
            if 'hidden_rate' in model_fields:
                available_read_fields.append('hidden_rate:avg')
                _logger.info("Используется hidden_rate для средних курсов")
            elif 'effective_rate' in model_fields:
                available_read_fields.append('effective_rate:avg')
                _logger.info("Используется effective_rate для средних курсов")
            elif 'rate_field' in model_fields:
                available_read_fields.append('rate_field:avg')
                _logger.info("Используется rate_field для средних курсов")
            
            # Фильтры для исключения кэш валют
            exclude_currencies = [
                'aed_cashe', 'cny_cashe', 'euro_cashe', 
                'rub_cashe', 'thb_cashe', 'usd_cashe', 'usdt_cashe'
            ]
            
            # Формируем базовый домен с проверкой существования полей
            base_domain = [('currency', '!=', False)]
            
            if 'hidden_hadge' in model_fields:
                base_domain.append(('hidden_hadge', '=', False))
            if 'prefix' in model_fields:
                base_domain.append(('prefix', '=', False))
            if 'hide_in_dashboard' in model_fields:
                base_domain.append(('hide_in_dashboard', '!=', True))
                
            base_domain.extend([('currency', 'not in', exclude_currencies)])
            
            # Группируем по валютам и получаем суммы и средние курсы с применением всех фильтров
            currency_groups = zayavka_model.read_group(
                domain + base_domain,
                available_read_fields,
                ['currency']
            )
            
            _logger.info(f"Получено {len(currency_groups)} групп валют")
            
            # Инициализируем результаты
            currency_sums = {'usd': 0, 'cny': 0, 'euro': 0, 'aed': 0, 'usdt': 0, 'rub': 0, 'thb': 0}
            average_rates = {'usd': "0", 'cny': "0", 'euro': "0", 'aed': "0", 'usdt': "0", 'rub': "0", 'thb': "0"}
            
            # Общее количество заявок с применением всех фильтров и таймаутом
            try:
                with self.env.cr.savepoint():
                    total_count = zayavka_model.search_count(domain + base_domain)
            except Exception as count_error:
                _logger.error(f"Ошибка подсчета общего количества заявок: {count_error}")
                total_count = 0
            
            # Обрабатываем группы валют с защитой от ошибок
            for group in currency_groups:
                try:
                    currency = group.get('currency')
                    if not currency:
                        continue
                        
                    amount_sum = group.get('amount', 0) or 0
                    
                    # Пробуем получить hidden_rate, потом effective_rate, потом rate_field
                    rate_avg = 0
                    if 'hidden_rate' in group:
                        rate_avg = group.get('hidden_rate', 0) or 0
                    elif 'effective_rate' in group:
                        rate_avg = group.get('effective_rate', 0) or 0
                    elif 'rate_field' in group:
                        rate_avg = group.get('rate_field', 0) or 0
                    
                    # Проверяем на валидность числовых значений
                    if not isinstance(amount_sum, (int, float)):
                        _logger.warning(f"Некорректная сумма для валюты {currency}: {amount_sum}")
                        amount_sum = 0
                        
                    if not isinstance(rate_avg, (int, float)):
                        _logger.warning(f"Некорректный курс для валюты {currency}: {rate_avg}")
                        rate_avg = 0
                        
                except Exception as group_error:
                    _logger.error(f"Ошибка обработки группы валют: {group_error}")
                    continue
                
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
            # Проверяем существование модели
            if 'amanat.zayavka' not in self.env:
                _logger.error("Модель amanat.zayavka не найдена в _get_today_orders_list")
                return []
            
            zayavka_model = self.env['amanat.zayavka']
            today = date.today()
            
            # Проверяем существование поля rate_fixation_date
            if 'rate_fixation_date' not in zayavka_model._fields:
                _logger.error("Поле rate_fixation_date не найдено в модели amanat.zayavka")
                # Используем create_date как альтернативу
                domain = [('create_date', '>=', datetime.combine(today, datetime.min.time())),
                         ('create_date', '<', datetime.combine(today + timedelta(days=1), datetime.min.time()))]
                _logger.info("Используется create_date вместо rate_fixation_date для фильтрации по дате")
            else:
                domain = [('rate_fixation_date', '=', today)]
            
            # Фильтры для исключения кэш валют и других условий
            exclude_currencies = [
                'aed_cashe', 'cny_cashe', 'euro_cashe', 
                'rub_cashe', 'thb_cashe', 'usd_cashe', 'usdt_cashe'
            ]
            
            # Формируем домен с проверкой существования полей
            additional_domain = []
            model_fields = zayavka_model._fields.keys()
            
            if 'hidden_hadge' in model_fields:
                additional_domain.append(('hidden_hadge', '=', False))
            if 'currency' in model_fields:
                additional_domain.extend([
                    ('currency', 'not in', exclude_currencies),
                    ('currency', '!=', False)
                ])
            if 'prefix' in model_fields:
                additional_domain.append(('prefix', '=', False))
            if 'hide_in_dashboard' in model_fields:
                additional_domain.append(('hide_in_dashboard', '!=', True))
            
            # Получаем заявки за сегодня с ограничением по количеству для производительности
            try:
                with self.env.cr.savepoint():
                    orders = zayavka_model.search(
                        domain + additional_domain, 
                        order='create_date desc',
                        limit=1000  # Ограничиваем количество записей для производительности
                    )
            except Exception as search_error:
                _logger.error(f"Ошибка поиска заявок за сегодня: {search_error}")
                return []
            
            orders_list = []
            for order in orders:
                try:
                    # Безопасное получение атрибутов заказа
                    order_currency = getattr(order, 'currency', None)
                    order_amount = getattr(order, 'amount', 0)
                    order_rate_field = getattr(order, 'hidden_rate', 0) or getattr(order, 'rate_field', 0) or getattr(order, 'effective_rate', 0)
                    order_status = getattr(order, 'status', '')
                    order_deal_type = getattr(order, 'deal_type', '')
                    order_payment_conditions = getattr(order, 'payment_conditions', '')
                    order_comment = getattr(order, 'comment', '')
                    order_zayavka_num = getattr(order, 'zayavka_num', '')
                    
                    # Безопасное получение связанных объектов
                    try:
                        contragent_name = order.contragent_id.name if hasattr(order, 'contragent_id') and order.contragent_id else ''
                    except Exception:
                        contragent_name = ''
                        
                    try:
                        agent_names = ', '.join(order.manager_ids.mapped('name')) if hasattr(order, 'manager_ids') and order.manager_ids else ''
                    except Exception:
                        agent_names = ''
                    
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
                    currency_display = currency_map.get(order_currency, order_currency or 'Не указана')
                    
                    # Тип сделки
                    deal_type_map = {
                        'import': 'Перевод',
                        'export': 'Экспорт', 
                        'import_export': 'Импорт-экспорт',
                        'export_import': 'Экспорт-импорт'
                    }
                    deal_type_display = deal_type_map.get(order_deal_type, order_deal_type or 'Перевод')
                    
                    # Статус с декорациями как в list view
                    status_class = ''
                    if order_status == '21':
                        status_class = 'table-success'  # decoration-success
                    elif order_status == '22':
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

                    # Безопасное форматирование числовых значений
                    try:
                        amount_formatted = f"{order_amount:,.0f}".replace(',', ' ') if order_amount and isinstance(order_amount, (int, float)) else "0"
                    except (ValueError, TypeError):
                        amount_formatted = "0"
                        
                    try:
                        rate_formatted = f"{order_rate_field:,.4f}".replace('.', ',') if order_rate_field and isinstance(order_rate_field, (int, float)) else "0,0000"
                    except (ValueError, TypeError):
                        rate_formatted = "0,0000"

                    orders_list.append({
                        'id': getattr(order, 'id', 0),
                        'zayavka_num': order_zayavka_num or '',
                        'contragent_name': contragent_name,
                        'agent_name': agent_names,
                        'amount': amount_formatted,
                        'currency_display': currency_display,
                        'rate_field': rate_formatted,
                        'payment_conditions_display': payment_conditions_map.get(order_payment_conditions, order_payment_conditions or ''),
                        'comment': order_comment or '',
                        'status_display': status_map.get(order_status, order_status or ''),
                        'status_class': status_class
                    })
                    
                except Exception as order_error:
                    _logger.error(f"Ошибка обработки заявки {getattr(order, 'id', 'unknown')}: {order_error}")
                    continue
            
            _logger.info(f"Получено {len(orders_list)} заявок за сегодня")
            return orders_list
            
        except Exception as e:
            _logger.error(f"Ошибка получения списка заявок за сегодня: {e}")
            return []
    
    def _calculate_usd_equivalents_optimized(self, currency_sums):
        """
        Оптимизированный подсчет эквивалентов в долларах с защитой от ошибок
        """
        try:
            # Проверяем валидность входных данных
            if not isinstance(currency_sums, dict):
                _logger.error(f"Некорректный тип currency_sums: {type(currency_sums)}")
                return {'total': 0, 'cny': 0, 'euro': 0, 'rub': 0, 'thb': 0}
            
            # Безопасное получение значений валют с проверкой на None и числовые типы
            def safe_get_amount(currency_key):
                amount = currency_sums.get(currency_key, 0)
                if not isinstance(amount, (int, float)) or amount is None:
                    _logger.warning(f"Некорректная сумма для {currency_key}: {amount}")
                    return 0.0
                return float(amount)
            
            usd_amount = safe_get_amount('usd')
            cny_amount = safe_get_amount('cny')
            euro_amount = safe_get_amount('euro')
            aed_amount = safe_get_amount('aed')
            rub_amount = safe_get_amount('rub')
            thb_amount = safe_get_amount('thb')
            
            # Используем фиксированные курсы для быстрого расчета с защитой от деления на ноль
            try:
                cny_to_usd = cny_amount / 7.2 if cny_amount > 0 else 0.0  # Примерный курс CNY к USD
            except ZeroDivisionError:
                cny_to_usd = 0.0
                
            try:
                euro_to_usd = euro_amount * 1.1 if euro_amount > 0 else 0.0  # Примерный курс EUR к USD
            except (ZeroDivisionError, TypeError):
                euro_to_usd = 0.0
                
            try:
                aed_to_usd = aed_amount / 3.67 if aed_amount > 0 else 0.0  # Примерный курс AED к USD
            except ZeroDivisionError:
                aed_to_usd = 0.0
                
            try:
                rub_to_usd = rub_amount / 92.0 if rub_amount > 0 else 0.0  # Примерный курс RUB к USD
            except ZeroDivisionError:
                rub_to_usd = 0.0
                
            try:
                thb_to_usd = thb_amount / 34.5 if thb_amount > 0 else 0.0  # Примерный курс THB к USD
            except ZeroDivisionError:
                thb_to_usd = 0.0
            
            # Общая сумма в USD (USDT не включается в эквивалент USD)
            total_usd = usd_amount + cny_to_usd + euro_to_usd + aed_to_usd + rub_to_usd + thb_to_usd
            
            return {
                'total': round(total_usd, 2),
                'cny': round(cny_to_usd, 2),
                'euro': round(euro_to_usd, 2),
                'rub': round(rub_to_usd, 2),
                'thb': round(thb_to_usd, 2)
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
    
 