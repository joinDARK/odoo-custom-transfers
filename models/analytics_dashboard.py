# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AnalyticsDashboard(models.Model):
    _name = 'amanat.analytics_dashboard'
    _description = 'Аналитический дашборд'
    
    name = fields.Char('Название', required=True, default='Диапазон')
    date_from = fields.Date('Дата начало', default=lambda self: fields.Date.today() - relativedelta(months=1))
    date_to = fields.Date('Дата конец', default=fields.Date.today)
    
    @api.model
    def get_analytics_data(self, date_from=None, date_to=None):
        """Получение данных аналитики для диапазона дат"""
        try:
            # Определяем диапазон дат
            if not date_from:
                date_from = fields.Date.today() - relativedelta(months=1)
            if not date_to:
                date_to = fields.Date.today()
            
            # Конвертируем строки в даты если нужно
            if isinstance(date_from, str):
                date_from = fields.Date.from_string(date_from)
            if isinstance(date_to, str):
                date_to = fields.Date.from_string(date_to)
            
            _logger.info(f"Analytics data requested for period: {date_from} - {date_to}")
            
            return {
                'success': True,
                'data': {
                    'date_from': str(date_from),
                    'date_to': str(date_to),
                    'period_info': f"Данные за период с {date_from} по {date_to}"
                }
            }
            
        except Exception as e:
            _logger.error(f"Error getting analytics data: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    @api.model
    def get_currency_rates(self):
        """Получение курсов валют к доллару - сначала пользовательские, потом от API, потом из последней записи"""
        try:
            # Сначала пытаемся получить кэшированные курсы (пользовательские имеют приоритет над API)
            cached_result = self._get_cached_api_rates()
            if cached_result.get('success') and cached_result.get('data'):
                return cached_result
            
            # Если нет кэшированных данных, ищем последнюю запись курсов
            latest_rate = self.env['amanat.rates'].search([], order='create_date desc', limit=1)
            
            if latest_rate:
                # Универсальная логика: проверяем формат курсов по их значениям
                _logger.info(f"Found amanat.rates record with RUB rate: {latest_rate.rub}")
                
                # Формируем данные курсов, проверяя формат по значениям
                rates_data = {}
                
                # Словарь полей модели и их значений
                rate_fields = {
                    'euro': latest_rate.euro,
                    'cny': latest_rate.cny,
                    'rub': latest_rate.rub,
                    'aed': latest_rate.aed,
                    'thb': latest_rate.thb,
                    'usd': latest_rate.usd,
                    'usdt': latest_rate.usdt
                }
                
                # Курсы по умолчанию на случай отсутствия данных
                default_rates = {
                    'euro': 1.0900,
                    'cny': 0.1400,
                    'rub': 0.0120,
                    'aed': 0.2700,
                    'thb': 0.0300,
                    'usd': 1.0000,
                    'usdt': 1.0000
                }
                
                for currency, rate_value in rate_fields.items():
                    if rate_value and rate_value > 0:
                        if currency in ['usd', 'usdt']:
                            # Доллар и USDT всегда 1.0000
                            formatted_rate = "1,0000"
                        elif rate_value > 1:
                            # Старый формат (сколько единиц валюты за 1 доллар) - инвертируем
                            usd_rate = 1.0 / rate_value
                            formatted_rate = f"{usd_rate:.4f}".replace('.', ',')
                            _logger.info(f"Inverted {currency.upper()} from amanat.rates: {rate_value} -> {usd_rate:.4f}")
                        else:
                            # Новый формат (сколько долларов стоит 1 единица валюты) - используем как есть
                            formatted_rate = f"{rate_value:.4f}".replace('.', ',')
                            _logger.info(f"Using {currency.upper()} from amanat.rates as-is: {rate_value}")
                    else:
                        # Если нет данных, используем значение по умолчанию
                        default_value = default_rates[currency]
                        formatted_rate = f"{default_value:.4f}".replace('.', ',')
                        _logger.info(f"Using default rate for {currency.upper()}: {default_value}")
                    
                    rates_data[currency] = formatted_rate
                
                _logger.info(f"Currency rates loaded from amanat.rates: {rates_data}")
                
                return {
                    'success': True,
                    'data': rates_data
                }
            else:
                # Возвращаем курсы по умолчанию если нет записей (сколько долларов стоит 1 единица валюты)
                default_rates = {
                    'euro': '1,0900',   # 1 EUR = 1.09 USD
                    'cny': '0,1400',    # 1 CNY = 0.14 USD
                    'rub': '0,0120',    # 1 RUB = 0.012 USD
                    'aed': '0,2700',    # 1 AED = 0.27 USD
                    'thb': '0,0300',    # 1 THB = 0.03 USD
                    'usd': '1,0000',    # 1 USD = 1.00 USD
                    'usdt': '1,0000'    # 1 USDT = 1.00 USD
                }
                
                _logger.warning("No currency rates found, using default USD-equivalent values")
                
                return {
                    'success': True,
                    'data': default_rates
                }
                
        except Exception as e:
            _logger.error(f"Error getting currency rates: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    

    def _convert_to_usd(self, amount, currency, currency_rates):
        """Общий метод для конвертации суммы в доллары"""
        if currency == 'usd':
            return amount
        rate = currency_rates.get(currency, 1.0)
        return amount * rate
    
    @api.model
    def get_contragents_balance(self, date_from=None, date_to=None):
        """Получение балансов контрагентов в рамках диапазона дат с расчетом в долларовом эквиваленте"""
        try:
            # Определяем диапазон дат - если даты не указаны, показываем за всё время
            use_date_filter = date_from or date_to  # Если хотя бы одна дата указана
            
            # Конвертируем строки в даты если нужно
            if date_from and isinstance(date_from, str):
                date_from = fields.Date.from_string(date_from)
            if date_to and isinstance(date_to, str):
                date_to = fields.Date.from_string(date_to)
            
            if use_date_filter:
                _logger.info(f"Contragents balance requested for period: {date_from} - {date_to}")
            else:
                _logger.info("Contragents balance requested for all time")
            
            # Получаем актуальные курсы валют для пересчета
            currency_rates_result = self.get_currency_rates()
            currency_rates = {}
            
            if currency_rates_result.get('success') and currency_rates_result.get('data'):
                rates_data = currency_rates_result['data']
                # Конвертируем курсы из строкового формата с запятой в float
                for currency, rate_str in rates_data.items():
                    try:
                        rate_float = float(rate_str.replace(',', '.'))
                        currency_rates[currency] = rate_float
                    except (ValueError, AttributeError):
                        _logger.warning(f"Invalid rate for {currency}: {rate_str}")
                        currency_rates[currency] = 1.0
            else:
                # Курсы по умолчанию если не удалось получить (сколько долларов стоит 1 единица валюты)
                currency_rates = {
                    'euro': 1.0900,   # 1 EUR = 1.09 USD
                    'cny': 0.1400,    # 1 CNY = 0.14 USD
                    'rub': 0.0120,    # 1 RUB = 0.012 USD
                    'aed': 0.2700,    # 1 AED = 0.27 USD
                    'thb': 0.0300,    # 1 THB = 0.03 USD
                    'usd': 1.0000,    # 1 USD = 1.00 USD
                    'usdt': 1.0000    # 1 USDT = 1.00 USD
                }
            
            _logger.info(f"Using currency rates for calculation: {currency_rates}")
            
            # Получаем контрагентов
            contragents = self.env['amanat.contragent'].search([])
            _logger.info(f"Found {len(contragents)} contragents in the system")
            
            balance_data = []
            for contragent in contragents:
                # Формируем домен для поиска сверок с учётом фильтра по датам
                domain = [('partner_id', '=', contragent.id)]
                if use_date_filter:
                    if date_from:
                        domain.append(('date', '>=', date_from))
                    if date_to:
                        domain.append(('date', '<=', date_to))
                
                # Получаем данные из СВЕРОК контрагента
                reconciliations = self.env['amanat.reconciliation'].search(domain)
                
                # Агрегируем суммы по валютам из всех сверок контрагента
                rub_balance = sum(reconciliations.mapped('sum_rub'))
                rub_cash_balance = sum(reconciliations.mapped('sum_rub_cashe'))
                usd_balance = sum(reconciliations.mapped('sum_usd'))
                usd_cash_balance = sum(reconciliations.mapped('sum_usd_cashe'))
                euro_balance = sum(reconciliations.mapped('sum_euro'))
                euro_cash_balance = sum(reconciliations.mapped('sum_euro_cashe'))
                cny_balance = sum(reconciliations.mapped('sum_cny'))
                cny_cash_balance = sum(reconciliations.mapped('sum_cny_cashe'))
                aed_balance = sum(reconciliations.mapped('sum_aed'))
                aed_cash_balance = sum(reconciliations.mapped('sum_aed_cashe'))
                usdt_balance = sum(reconciliations.mapped('sum_usdt'))
                thb_balance = sum(reconciliations.mapped('sum_thb'))
                thb_cash_balance = sum(reconciliations.mapped('sum_thb_cashe'))
                
                # Детальное логирование для отладки
                _logger.info(f"Contragent {contragent.name} ({contragent.id}): Found {len(reconciliations)} reconciliations")
                _logger.info(f"  RUB={rub_balance}, RUB_CASH={rub_cash_balance}, USD={usd_balance}, USD_CASH={usd_cash_balance}")
                _logger.info(f"  EUR={euro_balance}, EUR_CASH={euro_cash_balance}, CNY={cny_balance}, CNY_CASH={cny_cash_balance}")
                _logger.info(f"  AED={aed_balance}, AED_CASH={aed_cash_balance}, USDT={usdt_balance}, THB={thb_balance}, THB_CASH={thb_cash_balance}")
                
                # Рассчитываем общий баланс в долларах
                total_usd = 0
                total_usd += self._convert_to_usd(rub_balance, 'rub', currency_rates)
                total_usd += self._convert_to_usd(rub_cash_balance, 'rub', currency_rates)
                total_usd += self._convert_to_usd(aed_balance, 'aed', currency_rates)
                total_usd += self._convert_to_usd(aed_cash_balance, 'aed', currency_rates)
                total_usd += self._convert_to_usd(cny_balance, 'cny', currency_rates)
                total_usd += self._convert_to_usd(cny_cash_balance, 'cny', currency_rates)
                total_usd += self._convert_to_usd(euro_balance, 'euro', currency_rates)
                total_usd += self._convert_to_usd(euro_cash_balance, 'euro', currency_rates)
                total_usd += self._convert_to_usd(thb_balance, 'thb', currency_rates)
                total_usd += self._convert_to_usd(thb_cash_balance, 'thb', currency_rates)
                total_usd += self._convert_to_usd(usd_balance, 'usd', currency_rates)
                total_usd += self._convert_to_usd(usd_cash_balance, 'usd', currency_rates)
                total_usd += self._convert_to_usd(usdt_balance, 'usdt', currency_rates)
                
                # Формируем данные балансов для каждого контрагента
                balance_record = {
                    'id': contragent.id,
                    'name': contragent.name or f"Контрагент {contragent.id}",
                    'balance_usd': f"{total_usd:.2f}",
                    'balance_rub': f"{rub_balance:.3f}",
                    'balance_rub_cash': f"{rub_cash_balance:.3f}",
                    'balance_aed': f"{aed_balance:.3f}",
                    'balance_aed_cash': f"{aed_cash_balance:.3f}",
                    'balance_cny': f"{cny_balance:.3f}",
                    'balance_cny_cash': f"{cny_cash_balance:.3f}",
                    'balance_eur': f"{euro_balance:.3f}",
                    'balance_eur_cash': f"{euro_cash_balance:.3f}",
                    'balance_thb': f"{thb_balance:.3f}",
                    'balance_thb_cash': f"{thb_cash_balance:.3f}",
                    'balance_usd_cash': f"{usd_cash_balance:.3f}",
                    'balance_usdt': f"{usdt_balance:.3f}"
                }
                
                # Логируем данные для отладки
                _logger.info(f"Balance record for {contragent.name}: USD={total_usd:.2f}, RUB={rub_balance:.3f}, USDT={usdt_balance:.3f}")
                
                # Добавляем всех контрагентов, даже с нулевыми балансами
                balance_data.append(balance_record)
            
            # Если нет контрагентов, возвращаем пустой список
            if not balance_data:
                _logger.warning("No contragents found in the system")
                return {
                    'success': True,
                    'data': []
                }
            
            _logger.info(f"Contragents balance loaded: {len(balance_data)} records")
            
            return {
                'success': True,
                'data': balance_data
            }
            
        except Exception as e:
            _logger.error(f"Error getting contragents balance: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
        
    
    
    @api.model
    def get_contragents_balance_comparison(self, date_from1=None, date_to1=None, date_from2=None, date_to2=None):
        """Получение данных для сравнения балансов контрагентов между двумя диапазонами дат в долларовом эквиваленте"""
        try:
            # Определяем диапазоны дат - если даты не указаны, показываем за всё время
            use_date_filter1 = date_from1 or date_to1  # Если хотя бы одна дата указана для периода 1
            use_date_filter2 = date_from2 or date_to2  # Если хотя бы одна дата указана для периода 2
            
            # Конвертируем строки в даты если нужно
            if date_from1 and isinstance(date_from1, str):
                date_from1 = fields.Date.from_string(date_from1)
            if date_to1 and isinstance(date_to1, str):
                date_to1 = fields.Date.from_string(date_to1)
            if date_from2 and isinstance(date_from2, str):
                date_from2 = fields.Date.from_string(date_from2)
            if date_to2 and isinstance(date_to2, str):
                date_to2 = fields.Date.from_string(date_to2)
            
            if use_date_filter1 or use_date_filter2:
                _logger.info(f"Contragents balance comparison requested for periods: {date_from1} - {date_to1} vs {date_from2} - {date_to2}")
            else:
                _logger.info("Contragents balance comparison requested for all time vs all time")
            
            # Получаем актуальные курсы валют для пересчета
            currency_rates_result = self.get_currency_rates()
            currency_rates = {}
            
            if currency_rates_result.get('success') and currency_rates_result.get('data'):
                rates_data = currency_rates_result['data']
                # Конвертируем курсы из строкового формата с запятой в float
                for currency, rate_str in rates_data.items():
                    try:
                        rate_float = float(rate_str.replace(',', '.'))
                        currency_rates[currency] = rate_float
                    except (ValueError, AttributeError):
                        _logger.warning(f"Invalid rate for {currency}: {rate_str}")
                        currency_rates[currency] = 1.0
            else:
                # Курсы по умолчанию если не удалось получить
                currency_rates = {
                    'euro': 1.0900,   # 1 EUR = 1.09 USD
                    'cny': 0.1400,    # 1 CNY = 0.14 USD
                    'rub': 0.0120,    # 1 RUB = 0.012 USD
                    'aed': 0.2700,    # 1 AED = 0.27 USD
                    'thb': 0.0300,    # 1 THB = 0.03 USD
                    'usd': 1.0000,    # 1 USD = 1.00 USD
                    'usdt': 1.0000    # 1 USDT = 1.00 USD
                }
            

            
            # Получаем контрагентов
            contragents = self.env['amanat.contragent'].search([])
            
            comparison_data = []
            for contragent in contragents:
                # Формируем домен для поиска сверок первого периода с учётом фильтра по датам
                domain1 = [('partner_id', '=', contragent.id)]
                if use_date_filter1:
                    if date_from1:
                        domain1.append(('date', '>=', date_from1))
                    if date_to1:
                        domain1.append(('date', '<=', date_to1))
                
                # Формируем домен для поиска сверок второго периода с учётом фильтра по датам  
                domain2 = [('partner_id', '=', contragent.id)]
                if use_date_filter2:
                    if date_from2:
                        domain2.append(('date', '>=', date_from2))
                    if date_to2:
                        domain2.append(('date', '<=', date_to2))
                
                # Получаем сверки для первого периода
                reconciliations_1 = self.env['amanat.reconciliation'].search(domain1)
                
                # Получаем сверки для второго периода
                reconciliations_2 = self.env['amanat.reconciliation'].search(domain2)
                
                # Рассчитываем общие балансы для каждого периода в долларах
                def calculate_period_balance(reconciliations):
                    total = 0
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_rub')), 'rub', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_rub_cashe')), 'rub', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_usd')), 'usd', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_usd_cashe')), 'usd', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_euro')), 'euro', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_euro_cashe')), 'euro', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_cny')), 'cny', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_cny_cashe')), 'cny', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_aed')), 'aed', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_aed_cashe')), 'aed', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_thb')), 'thb', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_thb_cashe')), 'thb', currency_rates)
                    total += self._convert_to_usd(sum(reconciliations.mapped('sum_usdt')), 'usdt', currency_rates)
                    return total
                
                balance_comparison_1 = calculate_period_balance(reconciliations_1)
                balance_comparison_2 = calculate_period_balance(reconciliations_2)
                
                _logger.info(f"Comparison for {contragent.name}: Period1={len(reconciliations_1)} recs, Balance1=${balance_comparison_1:.2f}")
                _logger.info(f"  Period2={len(reconciliations_2)} recs, Balance2=${balance_comparison_2:.2f}")
                
                # Формируем данные сравнения для каждого контрагента
                comparison_record = {
                    'id': contragent.id,
                    'name': contragent.name or f"Контрагент {contragent.id}",
                    'balance_comparison_1': f"{balance_comparison_1:.2f}",
                    'balance_comparison_2': f"{balance_comparison_2:.2f}"
                }
                
                # Добавляем всех контрагентов, даже с нулевыми балансами
                comparison_data.append(comparison_record)
            
            # Если нет контрагентов, возвращаем пустой список
            if not comparison_data:
                _logger.warning("No contragents found in the system")
                return {
                    'success': True,
                    'data': [],
                    'period1': f"{date_from1} - {date_to1}",
                    'period2': f"{date_from2} - {date_to2}"
                }
            
            _logger.info(f"Contragents balance comparison loaded: {len(comparison_data)} records")
            
            return {
                'success': True,
                'data': comparison_data,
                'period1': f"{date_from1} - {date_to1}",
                'period2': f"{date_from2} - {date_to2}"
            }
            
        except Exception as e:
            _logger.error(f"Error getting contragents balance comparison: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'period1': '',
                'period2': ''
            }
        
    
    
    @api.model 
    def get_currency_rates_from_api(self):
        """Получение курсов валют через HTTP API"""
        try:
            import json
            from urllib.request import urlopen
            from urllib.error import URLError, HTTPError
            import socket
            
            # URL для получения курсов валют
            url = "http://localhost:8081/api/currency/rates"
            
            _logger.info(f"Запрашиваю курсы валют с API: {url}")
            
            # Делаем GET запрос с таймаутом
            try:
                response = urlopen(url, timeout=15)
                
                if response.getcode() == 200:
                    # Читаем и парсим JSON ответ
                    response_data = response.read().decode('utf-8')
                    data = json.loads(response_data)
                    
                    _logger.info(f"Успешно получены курсы валют. Базовая валюта: {data.get('base_currency', 'N/A')}")
                    _logger.info(f"Дата: {data.get('timestamp', 'N/A')}")
                    _logger.info(f"Количество валют: {data.get('count', 0)}")
                    
                    # Извлекаем курсы из ответа
                    rates = data.get('rates', {})
                    base_currency = data.get('base_currency', 'USD')
                    
                    if rates:
                        # Конвертируем в нужный формат с запятыми
                        rates_data = {}
                        
                        # Универсальная логика: если курс > 1, значит это старый формат и нужно инвертировать
                        for currency_code, rate_value in rates.items():
                            currency_key = currency_code.lower()
                            rate_float = float(rate_value)
                            
                            if currency_key in ['usd', 'usdt']:
                                # Доллар и USDT всегда 1.0000
                                formatted_rate = "1,0000"
                            elif rate_float > 1:
                                # Старый формат (сколько единиц валюты за 1 доллар) - инвертируем
                                usd_rate = 1.0 / rate_float
                                formatted_rate = f"{usd_rate:.4f}".replace('.', ',')
                                _logger.info(f"Inverted {currency_key.upper()}: {rate_float} -> {usd_rate:.4f}")
                            else:
                                # Новый формат (сколько долларов стоит 1 единица валюты) - используем как есть
                                formatted_rate = f"{rate_float:.4f}".replace('.', ',')
                                _logger.info(f"Using {currency_key.upper()} as-is: {rate_float}")
                            
                            rates_data[currency_key] = formatted_rate
                        
                        # Убеждаемся что есть все нужные валюты (относительно доллара)
                        default_rates = {
                            'euro': '1,0900',   # 1 EUR = 1.09 USD
                            'cny': '0,1400',    # 1 CNY = 0.14 USD  
                            'rub': '0,0120',    # 1 RUB = 0.012 USD
                            'aed': '0,2700',    # 1 AED = 0.27 USD
                            'thb': '0,0300',    # 1 THB = 0.03 USD
                            'usd': '1,0000',    # 1 USD = 1.00 USD (базовая валюта)
                            'usdt': '1,0000'    # 1 USDT = 1.00 USD
                        }
                        
                        # Дополняем недостающие валюты значениями по умолчанию
                        for currency, default_rate in default_rates.items():
                            if currency not in rates_data:
                                rates_data[currency] = default_rate
                        
                        # Сохраняем в кэш как автоматические курсы
                        self._save_api_rates(rates_data, is_user_defined=False)
                        
                        _logger.info("Курсы валют успешно получены:")
                        for currency, rate in rates_data.items():
                            _logger.info(f"  {currency.upper()}: {rate}")
                        
                        return {
                            'success': True,
                            'data': rates_data
                        }
                    else:
                        _logger.warning("В ответе API нет данных о курсах")
                        return {
                            'success': False,
                            'error': 'В ответе API нет данных о курсах',
                            'data': {}
                        }
                else:
                    _logger.error(f"Ошибка API. Статус: {response.getcode()}")
                    return {
                        'success': False,
                        'error': f'Ошибка API. Статус: {response.getcode()}',
                        'data': {}
                    }
            
            except HTTPError as e:
                _logger.error(f"HTTP ошибка: {e.code} - {e.reason}")
                return {
                    'success': False,
                    'error': f'HTTP ошибка: {e.code} - {e.reason}',
                    'data': {}
                }
            except URLError as e:
                _logger.error(f"Ошибка URL: {e.reason}")
                return {
                    'success': False,
                    'error': f'Ошибка подключения: {e.reason}',
                    'data': {}
                }
            except socket.timeout:
                _logger.error("Превышено время ожидания ответа от API")
                return {
                    'success': False,
                    'error': 'Превышено время ожидания ответа от API',
                    'data': {}
                }
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            _logger.error(f"Критическая ошибка при получении курсов валют:")
            _logger.error(f"Тип ошибки: {type(e).__name__}")
            _logger.error(f"Сообщение: {str(e)}")
            _logger.error(f"Полная трассировка:\n{error_details}")
            return {
                'success': False,
                'error': f'Ошибка при получении курсов валют: {str(e)}',
                'data': {}
            }
    
    def _save_api_rates(self, rates_data, is_user_defined=False):
        """Сохранение курсов валют в системные параметры"""
        try:
            import json
            from datetime import datetime
            
            # Определяем ключ параметра в зависимости от типа курсов
            param_key = 'amanat.user_currency_rates_cache' if is_user_defined else 'amanat.api_currency_rates_cache'
            
            # Добавляем timestamp к данным
            cache_data = {
                'rates': rates_data,
                'timestamp': datetime.now().isoformat(),
                'source': 'user' if is_user_defined else 'api',
                'is_user_defined': is_user_defined
            }
            
            # Сохраняем в системные параметры
            self.env['ir.config_parameter'].sudo().set_param(
                param_key,
                json.dumps(cache_data)
            )
            
            source_type = 'user-defined' if is_user_defined else 'API'
            _logger.info(f"{source_type} currency rates cached: {rates_data}")
            
        except Exception as e:
            _logger.error(f"Error saving rates to cache: {str(e)}")
    
    def _get_cached_api_rates(self):
        """Получение кэшированных курсов валют"""
        try:
            import json
            from datetime import datetime, timedelta
            
            # Сначала пытаемся получить пользовательские курсы
            user_cache_json = self.env['ir.config_parameter'].sudo().get_param(
                'amanat.user_currency_rates_cache',
                default=''
            )
            
            if user_cache_json:
                try:
                    user_cache_data = json.loads(user_cache_json)
                    rates_data = user_cache_data.get('rates')
                    if rates_data:
                        _logger.info("Using user-defined currency rates")
                        return {
                            'success': True,
                            'data': rates_data
                        }
                except json.JSONDecodeError:
                    _logger.warning("Invalid user currency rates cache, ignoring")
            
            # Если пользовательских курсов нет, пытаемся получить курсы от API
            api_cache_json = self.env['ir.config_parameter'].sudo().get_param(
                'amanat.api_currency_rates_cache',
                default=''
            )
            
            if api_cache_json:
                try:
                    api_cache_data = json.loads(api_cache_json)
                    
                    # Проверяем возраст кэша (не старше 24 часов)
                    cache_timestamp = datetime.fromisoformat(api_cache_data.get('timestamp', ''))
                    max_age = datetime.now() - timedelta(hours=24)
                    
                    if cache_timestamp >= max_age:
                        rates_data = api_cache_data.get('rates')
                        if rates_data:
                            _logger.info("Using cached API currency rates")
                            return {
                                'success': True,
                                'data': rates_data
                            }
                    else:
                        _logger.info("API currency rates cache is too old")
                        
                except (json.JSONDecodeError, ValueError):
                    _logger.warning("Invalid API currency rates cache, ignoring")
            
            # Если нет курсов в кэше, возвращаем ошибку
            _logger.warning("No cached currency rates found")
            return {
                'success': False,
                'error': 'Кэшированные курсы валют не найдены',
                'data': {}
            }
                
        except Exception as e:
            _logger.error(f"Ошибка получения кэшированных курсов валют: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    @api.model
    def save_user_currency_rates(self, rates):
        """Сохранение пользовательских курсов валют"""
        try:
            _logger.info(f"Saving user currency rates: {rates}")
            
            # Валидируем входные данные
            if not rates or not isinstance(rates, dict):
                return {
                    'success': False,
                    'error': 'Некорректные данные курсов валют'
                }
            
            # Проверяем наличие всех необходимых валют
            required_currencies = ['euro', 'cny', 'rub', 'aed', 'thb', 'usd', 'usdt']
            for currency in required_currencies:
                if currency not in rates:
                    return {
                        'success': False,
                        'error': f'Отсутствует курс для валюты: {currency}'
                    }
            
            # Валидируем и нормализуем значения курсов
            normalized_rates = {}
            for currency, rate_value in rates.items():
                try:
                    # Конвертируем строку в float, поддерживая запятую как разделитель
                    if isinstance(rate_value, str):
                        rate_value = rate_value.replace(',', '.')
                    
                    rate_float = float(rate_value)
                    
                    # Проверяем разумность значений курса
                    if rate_float <= 0 or rate_float > 1000:
                        return {
                            'success': False,
                            'error': f'Некорректное значение курса для {currency}: {rate_value}'
                        }
                    
                    # Сохраняем в формате с запятой
                    normalized_rates[currency] = f"{rate_float:.4f}".replace('.', ',')
                    
                except (ValueError, TypeError):
                    return {
                        'success': False,
                        'error': f'Некорректный формат курса для {currency}: {rate_value}'
                    }
            
            # Сохраняем пользовательские курсы в кэш
            self._save_api_rates(normalized_rates, is_user_defined=True)
            
            _logger.info(f"User currency rates saved successfully: {normalized_rates}")
            
            return {
                'success': True,
                'data': normalized_rates
            }
            
        except Exception as e:
            _logger.error(f"Error saving user currency rates: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @api.model
    def reset_currency_rates(self):
        """Сброс курсов валют к автоматическим значениям"""
        try:
            _logger.info("Resetting currency rates to automatic values")
            
            # Очищаем пользовательские курсы, чтобы заставить использовать API курсы
            self.env['ir.config_parameter'].sudo().set_param(
                'amanat.user_currency_rates_cache',
                ''
            )
            _logger.info("User-defined currency rates cache cleared")
            
            # Пытаемся получить свежие курсы от API
            api_result = self.get_currency_rates_from_api()
            
            if api_result.get('success') and api_result.get('data'):
                _logger.info("Currency rates reset to fresh API values")
                return api_result
            else:
                # Если API недоступен, возвращаем курсы по умолчанию
                default_rates = {
                    'euro': '1,0900',   # 1 EUR = 1.09 USD
                    'cny': '0,1400',    # 1 CNY = 0.14 USD
                    'rub': '0,0120',    # 1 RUB = 0.012 USD
                    'aed': '0,2700',    # 1 AED = 0.27 USD
                    'thb': '0,0300',    # 1 THB = 0.03 USD
                    'usd': '1,0000',    # 1 USD = 1.00 USD
                    'usdt': '1,0000'    # 1 USDT = 1.00 USD
                }
                
                # Сохраняем курсы по умолчанию в кэш
                self._save_api_rates(default_rates, is_user_defined=False)
                
                _logger.info("Currency rates reset to default values")
                
                return {
                    'success': True,
                    'data': default_rates
                }
                
        except Exception as e:
            _logger.error(f"Error resetting currency rates: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }