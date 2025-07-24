# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date, timedelta
import logging

_logger = logging.getLogger(__name__)

class ZayavkaFiksDashboard(models.Model):
    _name = 'amanat.zayavka_fiks_dashboard'
    _description = 'Дашборд Фикс Заявки'
    
    name = fields.Char(string='Название', default='Дашборд Фикс Заявки')
    
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
                _logger.info(f"Добавлен фильтр: дата >= {date_from}")
            else:
                date_from = None
                
            if date_to and date_to.strip():
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                domain.append(('rate_fixation_date', '<=', date_to))
                _logger.info(f"Добавлен фильтр: дата <= {date_to}")
            else:
                date_to = None
            
            if not domain:
                _logger.info("Фильтры по датам не заданы - показываем все заявки")
            
            zayavki = self.env['amanat.zayavka'].search(domain)
            _logger.info(f"Найдено {len(zayavki)} заявок")
            
            # Логируем подробную информацию о найденных заявках
            if zayavki:
                _logger.info(f"Первые 5 заявок:")
                for z in zayavki[:5]:
                    _logger.info(f"  - ID: {z.id}, Валюта: {z.currency}, Сумма: {z.amount}")
            
            # Подсчитываем статистику
            data = self._calculate_dashboard_metrics(zayavki, date_from, date_to)
            
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
    
    def _calculate_dashboard_metrics(self, zayavki, date_from, date_to):
        """
        Подсчет метрик дашборда
        """
        # Базовые метрики
        total_count = len(zayavki)
        
        # Средние курсы по договору за период
        average_rates = self._get_average_rates_for_period(zayavki)
        
        # Суммы по валютам
        currency_sums = self._calculate_currency_sums(zayavki)
        
        # Эквиваленты в долларах
        usd_equivalents = self._calculate_usd_equivalents(zayavki)
        
        # Данные для графика
        chart_data = self._prepare_chart_data(currency_sums)
        
        # Данные за сегодня
        today_data = self._get_today_data()
        
        return {
            'date_from': date_from.strftime('%Y-%m-%d') if date_from else '',
            'date_to': date_to.strftime('%Y-%m-%d') if date_to else '',
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
            'chart_data': chart_data,
            'today_data': today_data
        }
    
    def _get_average_rates_for_period(self, zayavki):
        """
        Получение средних курсов по договору за период из заявок
        """
        try:
            _logger.info(f"Расчет средних курсов для {len(zayavki)} заявок")
            
            # Группируем заявки по валютам и считаем средние курсы
            rates = {}
            
            # USD курсы (используем лучший курс или курс по договору)
            usd_zayavki = zayavki.filtered(lambda z: z.currency in ['usd', 'usd_cashe'])
            _logger.info(f"Найдено {len(usd_zayavki)} USD заявок")
            if usd_zayavki:
                usd_rates = []
                for z in usd_zayavki:
                    # Проверяем оба поля курса на валидность
                    best_rate = z.best_rate if z.best_rate and z.best_rate > 0 else None
                    rate_field = z.rate_field if z.rate_field and z.rate_field > 0 else None
                    
                    # Используем лучший курс, если есть, иначе курс по полю
                    rate = best_rate or rate_field
                    
                    if rate and rate > 0:
                        usd_rates.append(rate)
                        _logger.info(f"  USD заявка {z.id}: курс {rate} (best_rate={z.best_rate}, rate_field={z.rate_field})")
                    else:
                        _logger.info(f"  USD заявка {z.id}: пропущена - нет валидного курса (best_rate={z.best_rate}, rate_field={z.rate_field})")
                        
                avg_usd = sum(usd_rates) / len(usd_rates) if usd_rates else None
                _logger.info(f"Средний USD курс: {avg_usd} (использовано {len(usd_rates)} заявок)")
            else:
                avg_usd = None
                _logger.info("USD заявки не найдены")
            
            # CNY курсы
            cny_zayavki = zayavki.filtered(lambda z: z.currency in ['cny', 'cny_cashe'])
            _logger.info(f"Найдено {len(cny_zayavki)} CNY заявок")
            if cny_zayavki:
                cny_rates = []
                for z in cny_zayavki:
                    best_rate = z.best_rate if z.best_rate and z.best_rate > 0 else None
                    rate_field = z.rate_field if z.rate_field and z.rate_field > 0 else None
                    rate = best_rate or rate_field
                    
                    if rate and rate > 0:
                        cny_rates.append(rate)
                        _logger.info(f"  CNY заявка {z.id}: курс {rate} (best_rate={z.best_rate}, rate_field={z.rate_field})")
                    else:
                        _logger.info(f"  CNY заявка {z.id}: пропущена - нет валидного курса (best_rate={z.best_rate}, rate_field={z.rate_field})")
                        
                avg_cny = sum(cny_rates) / len(cny_rates) if cny_rates else None
                _logger.info(f"Средний CNY курс: {avg_cny} (использовано {len(cny_rates)} заявок)")
            else:
                avg_cny = None
                _logger.info("CNY заявки не найдены")
            
            # EURO курсы
            euro_zayavki = zayavki.filtered(lambda z: z.currency in ['euro', 'euro_cashe'])
            _logger.info(f"Найдено {len(euro_zayavki)} EURO заявок")
            if euro_zayavki:
                euro_rates = []
                for z in euro_zayavki:
                    best_rate = z.best_rate if z.best_rate and z.best_rate > 0 else None
                    rate_field = z.rate_field if z.rate_field and z.rate_field > 0 else None
                    rate = best_rate or rate_field
                    
                    if rate and rate > 0:
                        euro_rates.append(rate)
                        _logger.info(f"  EURO заявка {z.id}: курс {rate} (best_rate={z.best_rate}, rate_field={z.rate_field})")
                    else:
                        _logger.info(f"  EURO заявка {z.id}: пропущена - нет валидного курса (best_rate={z.best_rate}, rate_field={z.rate_field})")
                        
                avg_euro = sum(euro_rates) / len(euro_rates) if euro_rates else None
                _logger.info(f"Средний EURO курс: {avg_euro} (использовано {len(euro_rates)} заявок)")
            else:
                avg_euro = None
                _logger.info("EURO заявки не найдены")
            
            # AED курсы
            aed_zayavki = zayavki.filtered(lambda z: z.currency in ['aed', 'aed_cashe'])
            _logger.info(f"Найдено {len(aed_zayavki)} AED заявок")
            if aed_zayavki:
                aed_rates = []
                for z in aed_zayavki:
                    best_rate = z.best_rate if z.best_rate and z.best_rate > 0 else None
                    rate_field = z.rate_field if z.rate_field and z.rate_field > 0 else None
                    rate = best_rate or rate_field
                    
                    if rate and rate > 0:
                        aed_rates.append(rate)
                        _logger.info(f"  AED заявка {z.id}: курс {rate} (best_rate={z.best_rate}, rate_field={z.rate_field})")
                    else:
                        _logger.info(f"  AED заявка {z.id}: пропущена - нет валидного курса (best_rate={z.best_rate}, rate_field={z.rate_field})")
                        
                avg_aed = sum(aed_rates) / len(aed_rates) if aed_rates else None
                _logger.info(f"Средний AED курс: {avg_aed} (использовано {len(aed_rates)} заявок)")
            else:
                avg_aed = None
                _logger.info("AED заявки не найдены")
            
            _logger.info(f"Итоговые средние курсы: USD={avg_usd}, CNY={avg_cny}, EURO={avg_euro}, AED={avg_aed}")
            
            # USDT курсы
            usdt_zayavki = zayavki.filtered(lambda z: z.currency in ['usdt', 'usdt_cashe'])
            _logger.info(f"Найдено {len(usdt_zayavki)} USDT заявок")
            if usdt_zayavki:
                usdt_rates = []
                for z in usdt_zayavki:
                    best_rate = z.best_rate if z.best_rate and z.best_rate > 0 else None
                    rate_field = z.rate_field if z.rate_field and z.rate_field > 0 else None
                    rate = best_rate or rate_field
                    
                    if rate and rate > 0:
                        usdt_rates.append(rate)
                        _logger.info(f"  USDT заявка {z.id}: курс {rate} (best_rate={z.best_rate}, rate_field={z.rate_field})")
                    else:
                        _logger.info(f"  USDT заявка {z.id}: пропущена - нет валидного курса (best_rate={z.best_rate}, rate_field={z.rate_field})")
                        
                avg_usdt = sum(usdt_rates) / len(usdt_rates) if usdt_rates else None
                _logger.info(f"Средний USDT курс: {avg_usdt} (использовано {len(usdt_rates)} заявок)")
            else:
                avg_usdt = None
                _logger.info("USDT заявки не найдены")
            
            _logger.info(f"Итоговые средние курсы: USD={avg_usd}, CNY={avg_cny}, EURO={avg_euro}, AED={avg_aed}, USDT={avg_usdt}")
            
            return {
                'usd': f"{avg_usd:,.4f}".replace('.', ',') if avg_usd else "0",
                'cny': f"{avg_cny:,.4f}".replace('.', ',') if avg_cny else "0",
                'euro': f"{avg_euro:,.4f}".replace('.', ',') if avg_euro else "0",
                'aed': f"{avg_aed:,.4f}".replace('.', ',') if avg_aed else "0",
                'usdt': f"{avg_usdt:,.4f}".replace('.', ',') if avg_usdt else "0"
            }
                
        except Exception as e:
            _logger.error(f"Ошибка получения средних курсов: {e}")
            return {
                'usd': "0",
                'cny': "0",
                'euro': "0",
                'aed': "0",
                'usdt': "0"
            }
    
    def _calculate_currency_sums(self, zayavki):
        """
        Подсчет сумм по валютам
        """
        try:
            _logger.info(f"Подсчет сумм по валютам для {len(zayavki)} заявок")
            
            sums = {
                'usd': 0,
                'cny': 0,
                'euro': 0,
                'aed': 0,
                'usdt': 0
            }
            
            for z in zayavki:
                amount = z.amount or 0
                if amount > 0:
                    if z.currency in ['usd', 'usd_cashe']:
                        sums['usd'] += amount
                        _logger.info(f"  USD заявка {z.id}: сумма {amount}")
                    elif z.currency in ['cny', 'cny_cashe']:
                        sums['cny'] += amount
                        _logger.info(f"  CNY заявка {z.id}: сумма {amount}")
                    elif z.currency in ['euro', 'euro_cashe']:
                        sums['euro'] += amount
                        _logger.info(f"  EURO заявка {z.id}: сумма {amount}")
                    elif z.currency in ['aed', 'aed_cashe']:
                        sums['aed'] += amount
                        _logger.info(f"  AED заявка {z.id}: сумма {amount}")
                    elif z.currency in ['usdt', 'usdt_cashe']:
                        sums['usdt'] += amount
                        _logger.info(f"  USDT заявка {z.id}: сумма {amount}")
            
            _logger.info(f"Итоговые суммы: USD={sums['usd']}, CNY={sums['cny']}, EURO={sums['euro']}, AED={sums['aed']}, USDT={sums['usdt']}")
            return sums
            
        except Exception as e:
            _logger.error(f"Ошибка подсчета сумм по валютам: {e}")
            return {'usd': 0, 'cny': 0, 'euro': 0, 'aed': 0, 'usdt': 0}
    
    def _calculate_usd_equivalents(self, zayavki):
        """
        Подсчет эквивалентов в долларах
        """
        try:
            _logger.info(f"Подсчет эквивалентов в долларах для {len(zayavki)} заявок")
            
            total_usd = 0
            cny_usd = 0
            euro_usd = 0
            
            for z in zayavki:
                if hasattr(z, 'usd_equivalent') and z.usd_equivalent:
                    # Если есть готовое поле с эквивалентом в USD
                    equivalent = z.usd_equivalent
                    total_usd += equivalent
                    _logger.info(f"  Заявка {z.id}: использую готовый эквивалент USD = {equivalent}")
                    
                    if z.currency in ['cny', 'cny_cashe']:
                        cny_usd += equivalent
                    elif z.currency in ['euro', 'euro_cashe']:
                        euro_usd += equivalent
                else:
                    # Рассчитываем сами, используя примерные курсы
                    if z.amount and z.currency:
                        amount = z.amount
                        if z.currency in ['usd', 'usd_cashe']:
                            usd_eq = amount
                        elif z.currency in ['cny', 'cny_cashe']:
                            usd_eq = amount / 7.2  # Примерный курс CNY к USD
                            cny_usd += usd_eq
                        elif z.currency in ['euro', 'euro_cashe']:
                            usd_eq = amount * 1.1  # Примерный курс EUR к USD
                            euro_usd += usd_eq
                        elif z.currency in ['aed', 'aed_cashe']:
                            usd_eq = amount / 3.67  # Примерный курс AED к USD
                        elif z.currency in ['usdt', 'usdt_cashe']:
                            usd_eq = 0  # USDT не учитывается в эквиваленте USD
                        else:
                            usd_eq = 0
                        
                        total_usd += usd_eq
                        _logger.info(f"  Заявка {z.id}: валюта {z.currency}, сумма {amount}, эквивалент USD = {usd_eq}")
            
            _logger.info(f"Итоговые эквиваленты USD: общий={total_usd}, CNY={cny_usd}, EURO={euro_usd}")
            
            return {
                'total': total_usd,
                'cny': cny_usd,
                'euro': euro_usd
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
            return {
                'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT'],
                'datasets': [{
                    'label': 'Сумма по валютам',
                    'data': [0, 0, 0, 0, 0],
                    'backgroundColor': ['#5b9bd5', '#70ad47', '#ffc000', '#7030a0', '#ff6b35']
                }]
            } 
    
    def _get_today_data(self):
        """
        Получение данных за сегодняшний день
        """
        try:
            today = date.today()
            _logger.info(f"Расчет данных за сегодня: {today}")
            
            # Получаем заявки за сегодня
            today_zayavki = self.env['amanat.zayavka'].search([
                ('rate_fixation_date', '=', today)
            ])
            
            _logger.info(f"Найдено {len(today_zayavki)} заявок за сегодня")
            
            if not today_zayavki:
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
                    'chart_data': {
                        'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT'],
                        'datasets': [{
                            'label': 'Сумма по валютам',
                            'data': [0, 0, 0, 0, 0],
                            'backgroundColor': ['#5b9bd5', '#70ad47', '#ffc000', '#7030a0', '#ff6b35']
                        }]
                    }
                }
            
            # Средние курсы за сегодня
            today_average_rates = self._get_average_rates_for_period(today_zayavki)
            
            # Суммы по валютам за сегодня
            today_currency_sums = self._calculate_currency_sums(today_zayavki)
            
            # Эквиваленты в долларах за сегодня
            today_usd_equivalents = self._calculate_usd_equivalents(today_zayavki)
            
            # Данные для графика за сегодня
            today_chart_data = self._prepare_today_chart_data(today_currency_sums)
            

            
            return {
                'average_rates': today_average_rates,
                'total_count': len(today_zayavki),
                'equivalent_usd': f"{today_usd_equivalents['total']:,.2f}",
                'cny_equivalent_usd': f"{today_usd_equivalents['cny']:,.2f}",
                'euro_equivalent_usd': f"{today_usd_equivalents['euro']:,.2f}",
                'usd_sum': f"{today_currency_sums['usd']:,.0f}",
                'cny_sum': f"{today_currency_sums['cny']:,.0f}",
                'euro_sum': f"{today_currency_sums['euro']:,.0f}",
                'aed_sum': f"{today_currency_sums['aed']:,.0f}",
                'usdt_sum': f"{today_currency_sums['usdt']:,.0f}",
                'chart_data': today_chart_data
            }
            
        except Exception as e:
            _logger.error(f"Ошибка получения данных за сегодня: {e}")
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
                'chart_data': {
                    'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT'],
                    'datasets': [{
                        'label': 'Сумма по валютам',
                        'data': [0, 0, 0, 0, 0],
                        'backgroundColor': ['#5b9bd5', '#70ad47', '#ffc000', '#7030a0', '#ff6b35']
                    }]
                }
            } 
    
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
            return {
                'labels': ['USD', 'CNY', 'EURO', 'AED', 'USDT'],
                'datasets': [{
                    'label': 'Сумма по валютам сегодня',
                    'data': [0, 0, 0, 0, 0],
                    'backgroundColor': ['#5b9bd5', '#70ad47', '#ffc000', '#7030a0', '#ff6b35']
                }]
            }
    
 