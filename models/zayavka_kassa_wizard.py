from odoo import models, fields, api
from datetime import datetime, timedelta
import requests
import json
import logging

_logger = logging.getLogger(__name__)


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
        """Применяет фильтр к заявкам и отправляет данные на сервер"""
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
            kassa_records = None
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
        
        # Получаем отфильтрованные заявки
        filtered_zayavkas = self.env['amanat.zayavka'].search(domain)
        
        # Отправляем данные на сервер и получаем информацию о результате
        server_response_info = self._send_data_to_server(filtered_zayavkas)
        
        # Формируем действие для открытия отфильтрованных заявок
        action = {
            'type': 'ir.actions.act_window',
            'name': f'Заявки - Касса: {self.kassa_type}',
            'res_model': 'amanat.zayavka',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'main',
            'context': {
                **self.env.context,
                'filtered_zayavkas_count': len(filtered_zayavkas),
                'kassa_filter_applied': True,
                'kassa_type': self.kassa_type,
                'filter_field': self.field_name,
                'date_from': self.date_from.isoformat() if self.date_from else None,
                'date_to': self.date_to.isoformat() if self.date_to else None,
                **server_response_info,  # Добавляем информацию о результате отправки на сервер
            },
        }
        
        return action

    def _send_data_to_server(self, zayavkas):
        """Отправляет данные заявок на внешний сервер"""
        data = []
        
        # Логируем количество входящих заявок
        _logger.info(f"Получено для отправки заявок: {len(zayavkas)}")
        if not zayavkas:
            _logger.warning("Список заявок для отправки пуст!")
            return {
                'server_response': 'No applications to send',
                'server_status': 'error',
                'sent_count': 0
            }
        
        try:
            # Подготавливаем данные для отправки
            for i, zayavka in enumerate(zayavkas):
                _logger.info(f"Обрабатываем заявку {i+1}/{len(zayavkas)}: {zayavka.zayavka_num}")
                # Вычисляем дополнительные поля
                expense_payment_currency = zayavka.amount * (zayavka.percent_from_payment_order_rule / 100) if zayavka.percent_from_payment_order_rule else 0
                reward_percent_minus_hidden = zayavka.hand_reward_percent - zayavka.hidden_commission if zayavka.hand_reward_percent and zayavka.hidden_commission else 0
                export_reward_currency = zayavka.amount * (zayavka.hand_reward_percent / 100) if zayavka.hand_reward_percent and zayavka.deal_type == 'export' else 0
                
                # Фин рез в % 
                fin_res_percent = 0
                if zayavka.deal_type == 'export':
                    fin_res_percent = (zayavka.fin_res_client_real / zayavka.amount) * 100 if zayavka.amount else 0
                else:
                    fin_res_percent = (zayavka.fin_res_client_real / zayavka.cost_of_money_client_real) * 100 if zayavka.cost_of_money_client_real else 0
                
                # Эквивалент доллара по XE
                usd_equivalent_xe = zayavka.amount * zayavka.xe_rate if zayavka.xe_rate else 0
                
                # Агентское вознаграждение наше (тезер)
                agent_reward_tezer = zayavka.hidden_commission * zayavka.amount if zayavka.hidden_commission else 0
                
                # Расход на операционную деятельность от инвойса
                invoice_operational_expense = zayavka.amount * (zayavka.percent_from_expense_rule / 100) if zayavka.percent_from_expense_rule else 0
                
                # Расход субагента
                subagent_expense = zayavka.amount * ((zayavka.price_list_carrying_out_accrual_percentage or 0) + (zayavka.price_list_profit_id.percent_accrual or 0)) / 100
                
                # Количество дней просрочки (разные для разных банков)
                days_overdue_sber = 0
                days_overdue_sovcom = 0
                days_overdue_individual = 0
                days_overdue_vtb = 0
                
                if zayavka.date_received_on_pc_payment and zayavka.rate_fixation_date:
                    days_diff = (zayavka.date_received_on_pc_payment - zayavka.rate_fixation_date).days
                    if zayavka.bank == 'sberbank':
                        days_overdue_sber = days_diff
                    elif zayavka.bank == 'sovcombank':
                        days_overdue_sovcom = days_diff
                    elif zayavka.bank == 'vtb':
                        days_overdue_vtb = days_diff
                    else:
                        days_overdue_individual = days_diff
                
                # Курс Джесс по валютам
                jess_rate_usd = zayavka.jess_rate if zayavka.currency == 'usd' else 0
                jess_rate_cny = zayavka.jess_rate if zayavka.currency == 'cny' else 0
                jess_rate_eur = zayavka.jess_rate if zayavka.currency == 'euro' else 0
                
                # Получаем русские названия для условий оплаты и вида сделки
                payment_conditions_dict = {
                    'accred': 'Аккредитив',
                    'prepayment': 'Предоплата',
                    'postpayment': 'Постоплата',
                    'escrow': 'Эскроу'
                }
                
                deal_type_dict = {
                    'import': 'Импорт',
                    'export': 'Экспорт'
                }
                
                # Получаем русские названия
                payment_conditions_ru = payment_conditions_dict.get(zayavka.payment_conditions, zayavka.payment_conditions) if zayavka.payment_conditions else None
                deal_type_ru = deal_type_dict.get(zayavka.deal_type, zayavka.deal_type) if zayavka.deal_type else None
                
                zayavka_data = {
                    # Основные данные
                    'zayavka_id': zayavka.zayavka_id,
                    'zayavka_num': zayavka.zayavka_num,
                    'status': zayavka.status,
                    'date_placement': zayavka.date_placement.isoformat() if zayavka.date_placement else None,
                    'taken_in_work_date': zayavka.taken_in_work_date.isoformat() if zayavka.taken_in_work_date else None,
                    
                    # Контрагенты
                    'contragent_id': zayavka.contragent_id.id if zayavka.contragent_id else None,
                    'contragent_name': zayavka.contragent_id.name if zayavka.contragent_id else None,
                    'subagent_ids': [subagent.id for subagent in zayavka.subagent_ids],
                    'subagent_names': [subagent.name for subagent in zayavka.subagent_ids],
                    'client_id': zayavka.client_id.id if zayavka.client_id else None,
                    'client_name': zayavka.client_id.name if zayavka.client_id else None,
                    'manager_ids': [manager.id for manager in zayavka.manager_ids],
                    'manager_names': [manager.name for manager in zayavka.manager_ids],
                    'subagent_payer_ids': [payer.id for payer in zayavka.subagent_payer_ids],
                    'subagent_payer_names': [payer.name for payer in zayavka.subagent_payer_ids],
                    
                    # Даты
                    'deal_closed_date': zayavka.deal_closed_date.isoformat() if zayavka.deal_closed_date else None,
                    'rate_fixation_date': zayavka.rate_fixation_date.isoformat() if zayavka.rate_fixation_date else None,
                    'date_received_on_pc_payment': zayavka.date_received_on_pc_payment.isoformat() if zayavka.date_received_on_pc_payment else None,
                    'date_received_tezera': zayavka.date_received_tezera.isoformat() if zayavka.date_received_tezera else None,
                    
                    # Суммы и валюты
                    'amount': zayavka.amount,
                    'currency': zayavka.currency,
                    'total_client': zayavka.total_client,
                    'equivalent_amount_usd': zayavka.equivalent_amount_usd,
                    'usd_equivalent_xe': usd_equivalent_xe,
                    
                    # Суммы по валютам
                    'amount_usd': zayavka.amount if zayavka.currency == 'usd' else 0,
                    'amount_cny': zayavka.amount if zayavka.currency == 'cny' else 0,
                    'amount_aed': zayavka.amount if zayavka.currency == 'aed' else 0,
                    'amount_thb': zayavka.amount if zayavka.currency == 'thb' else 0,
                    'amount_eur': zayavka.amount if zayavka.currency == 'euro' else 0,
                    'amount_idr': zayavka.amount if zayavka.currency == 'idr' else 0,
                    
                    # Проценты и комиссии
                    'hand_reward_percent': zayavka.hand_reward_percent,
                    'hidden_commission': zayavka.hidden_commission,
                    'reward_percent_minus_hidden': reward_percent_minus_hidden,
                    'hidden_partner_commission_real': zayavka.hidden_partner_commission_real,
                    'plus_dollar': zayavka.plus_dollar,
                    
                    # Курсы
                    'hidden_rate': zayavka.hidden_rate,
                    'rate_field': zayavka.rate_field,
                    'jess_rate': zayavka.jess_rate,
                    'jess_rate_usd': jess_rate_usd,
                    'jess_rate_cny': jess_rate_cny,
                    'jess_rate_eur': jess_rate_eur,
                    'xe_rate': zayavka.xe_rate,
                    
                    # Расходы
                    'conversion_expenses_currency': zayavka.conversion_expenses_currency,
                    'payment_order_rf_client': zayavka.payment_order_rf_client,
                    'expense_payment_currency': expense_payment_currency,
                    'client_payment_cost': zayavka.client_payment_cost,
                    'cost_of_money_client_real': zayavka.cost_of_money_client_real,
                    'client_real_operating_expenses': zayavka.client_real_operating_expenses,
                    'invoice_operational_expense': invoice_operational_expense,
                    'subagent_expense': subagent_expense,
                    
                    # Вознаграждения
                    'export_reward_currency': export_reward_currency,
                    'our_client_reward': zayavka.our_client_reward,
                    'non_our_client_reward': zayavka.non_our_client_reward,
                    'agent_our_reward': zayavka.agent_our_reward,
                    'agent_reward_tezer': agent_reward_tezer,
                    
                    # Финансовые результаты
                    'fin_res_client_real': zayavka.fin_res_client_real,
                    'fin_res_client_real_rub': zayavka.fin_res_client_real_rub,
                    'fin_res_percent': fin_res_percent,
                    
                    # Условия и типы
                    'payment_conditions': payment_conditions_ru,
                    'deal_type': deal_type_ru,
                    'with_accreditive': zayavka.with_accreditive,
                    'bank': zayavka.bank,
                    
                    # Дни просрочки
                    'days_overdue_sber': days_overdue_sber,
                    'days_overdue_sovcom': days_overdue_sovcom,
                    'days_overdue_individual': days_overdue_individual,
                    'days_overdue_vtb': days_overdue_vtb,
                    
                    # Комментарии
                    'comment': zayavka.comment,
                    
                    # Информация о фильтре
                    'kassa_type': self.kassa_type,
                    'filter_field': self.field_name,
                    'date_from': self.date_from.isoformat() if self.date_from else None,
                    'date_to': self.date_to.isoformat() if self.date_to else None,
                }
                data.append(zayavka_data)
            
            # Отправляем POST запрос на сервер
            api_url = "http://92.255.207.48:8085/api/salesRegisters"  # Используем HTTP вместо HTTPS
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Проверяем, что данные не пустые
            if not data:
                _logger.warning("Данные для отправки пустые!")
                return {
                    'server_response': 'No data to send',
                    'server_status': 'error',
                    'sent_count': 0
                }
            
            # Оборачиваем данные в объект, как ожидает сервер
            payload = {
                "data": data,  # Массив заявок в поле data
                "type": "financial_results",
                "fileName": self.kassa_type + "_" + self.field_name + "_" + self.date_from.isoformat(),
                "kassa_type": self.kassa_type,
                "filter_info": {
                    "field_name": self.field_name,
                    "date_from": self.date_from.isoformat() if self.date_from else None,
                    "date_to": self.date_to.isoformat() if self.date_to else None
                }
            }
            
            # Логируем структуру данных перед отправкой
            _logger.info(f"Структура payload для отправки: type={type(payload)}")
            _logger.info(f"Количество заявок в data: {len(data)}")
            _logger.info(f"Ключи payload: {list(payload.keys())}")
            
            # Пробуем отправить данные в формате объекта с массивом
            response = requests.post(
                api_url,
                json=payload,  # Отправляем объект с данными
                headers=headers,
                timeout=30
            )
            
            _logger.info(f"Отправлено {len(data)} заявок на сервер. Статус ответа: {response.status_code}")
            
            # Если сервер все еще ожидает просто массив, пробуем альтернативный формат
            if response.status_code == 400 and "массивом" in response.text:
                _logger.info("Пробуем отправить данные как простой массив...")
                
                response = requests.post(
                    api_url,
                    json=data,  # Отправляем просто массив
                    headers=headers,
                    timeout=30
                )
                _logger.info(f"Альтернативная отправка. Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                _logger.info(f"Успешный ответ от сервера: {response_data}")
                
                # Создаем запись в модели kassa_files
                kassa_files_model = self.env['amanat.kassa_files']
                kassa_file = kassa_files_model.create_from_server_response(
                    response_data,
                    self.kassa_type,
                    self.field_name,
                    self.date_from,
                    self.date_to
                )
                
                # Возвращаем информацию о результате
                return {
                    'server_response': response_data,
                    'server_status': 'success',
                    'sent_count': len(data),
                    'kassa_file_id': kassa_file.id if kassa_file else None,
                    'kassa_file_name': kassa_file.name if kassa_file else None
                }
            else:
                _logger.error(f"Ошибка при отправке данных на сервер: {response.status_code} - {response.text}")
                return {
                    'server_response': response.text,
                    'server_status': 'error',
                    'sent_count': len(data)
                }
        
        except requests.exceptions.RequestException as e:
            _logger.error(f"Ошибка подключения к серверу: {str(e)}")
            return {
                'server_response': str(e),
                'server_status': 'connection_error',
                'sent_count': len(data)
            }
        except Exception as e:
            _logger.error(f"Неожиданная ошибка при отправке данных: {str(e)}")
            return {
                'server_response': str(e),
                'server_status': 'unexpected_error',
                'sent_count': len(data)
            } 