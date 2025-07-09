import requests
import json
import time
import logging
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo import _

_logger = logging.getLogger(__name__)


class SwiftGpiClient:
    """Клиент для работы с Swift GPI API"""
    
    def __init__(self, config):
        """
        Инициализация клиента
        
        Args:
            config: объект amanat.swift.api.config
        """
        self.config = config
        self.session = requests.Session()
        self.oauth_token = None
        self.token_expires_at = None
        
        # Настройка таймаутов и повторов
        self.session.timeout = config.timeout
        
        # Настройка сертификатов если нужно
        if config.use_client_certificate and config.certificate_path and config.private_key_path:
            self.session.cert = (config.certificate_path, config.private_key_path)
            
        # Заголовки по умолчанию
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'OdooSwiftGpiClient/1.0'
        })

    def get_oauth_token(self):
        """Получить OAuth токен для API"""
        
        # Проверяем действующий токен
        if self.oauth_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.oauth_token
        
        try:
            # Данные для получения токена
            token_data = {
                'grant_type': 'client_credentials',
                'scope': 'https://swiftref.api.swift.com gpi'
            }
            
            # Аутентификация через Basic Auth
            auth = (self.config.consumer_key, self.config.consumer_secret)
            
            _logger.info(f"Запрос OAuth токена: {self.config.oauth_url}")
            
            response = self.session.post(
                self.config.oauth_url,
                data=token_data,
                auth=auth,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                token_info = response.json()
                self.oauth_token = token_info.get('access_token')
                
                # Вычисляем время истечения токена
                expires_in = token_info.get('expires_in', 3600)  # По умолчанию 1 час
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # Минус минута на всякий случай
                
                # Устанавливаем токен в заголовки
                self.session.headers['Authorization'] = f'Bearer {self.oauth_token}'
                
                _logger.info("OAuth токен получен успешно")
                self.config.record_api_call(success=True)
                
                return self.oauth_token
            else:
                error_msg = f"Ошибка получения OAuth токена: {response.status_code} - {response.text}"
                _logger.error(error_msg)
                self.config.record_api_call(success=False)
                raise UserError(_(error_msg))
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка сети при получении OAuth токена: {str(e)}"
            _logger.error(error_msg)
            self.config.record_api_call(success=False)
            raise UserError(_(error_msg))

    def get_payment_status(self, uetr):
        """
        Получить статус платежа по UETR
        
        Args:
            uetr: Unique End-to-End Transaction Reference
            
        Returns:
            dict: Информация о статусе платежа
        """
        
        if not uetr:
            raise ValidationError(_("UETR не может быть пустым"))
            
        # Валидация формата UETR (36 символов UUID)
        if len(uetr.replace('-', '')) != 32:
            raise ValidationError(_("Неверный формат UETR. Ожидается UUID (36 символов с дефисами)"))
        
        try:
            # Получаем токен
            token = self.get_oauth_token()
            if not token:
                raise UserError(_("Не удалось получить OAuth токен"))
            
            # Формируем URL для запроса статуса
            url = f"{self.config.api_base_url}/payments/{uetr}/status"
            
            _logger.info(f"Запрос статуса платежа: {url}")
            
            # Делаем запрос с повторами
            last_exception = None
            for attempt in range(self.config.max_retries):
                try:
                    response = self.session.get(url, timeout=self.config.timeout)
                    
                    if response.status_code == 200:
                        payment_data = response.json()
                        _logger.info(f"Получен статус платежа для UETR {uetr}")
                        self.config.record_api_call(success=True)
                        
                        return self._format_payment_status(payment_data)
                        
                    elif response.status_code == 404:
                        _logger.warning(f"Платеж с UETR {uetr} не найден")
                        self.config.record_api_call(success=False)
                        return {
                            'error': 'not_found',
                            'message': f'Платеж с UETR {uetr} не найден в системе',
                            'uetr': uetr,
                            'status': 'NOT_FOUND'
                        }
                        
                    elif response.status_code == 401:
                        # Токен истек, попробуем обновить
                        _logger.warning("OAuth токен истек, обновляем...")
                        self.oauth_token = None
                        self.token_expires_at = None
                        self.get_oauth_token()
                        continue
                        
                    else:
                        error_msg = f"Ошибка API: {response.status_code} - {response.text}"
                        _logger.error(error_msg)
                        if attempt == self.config.max_retries - 1:  # Последняя попытка
                            self.config.record_api_call(success=False)
                            return {
                                'error': 'api_error',
                                'message': error_msg,
                                'uetr': uetr,
                                'status': 'ERROR'
                            }
                        time.sleep(2 ** attempt)  # Экспоненциальная задержка
                        
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt < self.config.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        break
            
            # Если дошли сюда, все попытки неуспешны
            error_msg = f"Ошибка сети после {self.config.max_retries} попыток: {str(last_exception)}"
            _logger.error(error_msg)
            self.config.record_api_call(success=False)
            return {
                'error': 'network_error',
                'message': error_msg,
                'uetr': uetr,
                'status': 'ERROR'
            }
            
        except Exception as e:
            error_msg = f"Неожиданная ошибка при запросе статуса: {str(e)}"
            _logger.error(error_msg)
            self.config.record_api_call(success=False)
            return {
                'error': 'unexpected_error',
                'message': error_msg,
                'uetr': uetr,
                'status': 'ERROR'
            }

    def get_payment_tracking(self, uetr):
        """
        Получить детальную информацию отслеживания платежа
        
        Args:
            uetr: Unique End-to-End Transaction Reference
            
        Returns:
            dict: Детальная информация о маршруте платежа
        """
        
        if not uetr:
            raise ValidationError(_("UETR не может быть пустым"))
        
        try:
            # Получаем токен
            token = self.get_oauth_token()
            if not token:
                raise UserError(_("Не удалось получить OAuth токен"))
            
            # Формируем URL для запроса отслеживания
            url = f"{self.config.api_base_url}/payments/{uetr}/transactions"
            
            _logger.info(f"Запрос отслеживания платежа: {url}")
            
            response = self.session.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                tracking_data = response.json()
                _logger.info(f"Получены данные отслеживания для UETR {uetr}")
                self.config.record_api_call(success=True)
                
                return self._format_tracking_data(tracking_data)
                
            elif response.status_code == 404:
                _logger.warning(f"Отслеживание для UETR {uetr} не найдено")
                self.config.record_api_call(success=False)
                return {
                    'error': 'not_found',
                    'message': f'Отслеживание для UETR {uetr} не найдено',
                    'uetr': uetr
                }
            else:
                error_msg = f"Ошибка API отслеживания: {response.status_code} - {response.text}"
                _logger.error(error_msg)
                self.config.record_api_call(success=False)
                return {
                    'error': 'api_error',
                    'message': error_msg,
                    'uetr': uetr
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка сети при запросе отслеживания: {str(e)}"
            _logger.error(error_msg)
            self.config.record_api_call(success=False)
            return {
                'error': 'network_error',
                'message': error_msg,
                'uetr': uetr
            }

    def _format_payment_status(self, api_data):
        """Форматирование данных статуса от API"""
        
        # Маппинг Swift GPI статусов
        status_mapping = {
            'RJCT': {'status': 'REJECTED', 'emoji': '❌', 'description': 'Отклонен'},
            'ACSP': {'status': 'PROCESSING', 'emoji': '🟧', 'description': 'В обработке'},
            'ACCC': {'status': 'COMPLETED', 'emoji': '✅', 'description': 'Завершен'},
        }
        
        # Маппинг GPI кодов причин
        reason_code_mapping = {
            'G000': 'Передан следующему банку',
            'G001': 'Передан следующему банку (без отслеживания)',
            'G002': 'Ожидание кредитования',
            'G003': 'Ожидание документов от получателя',
            'G004': 'Ожидание поступления средств',
            'G005': 'Доставлен в банк получателя как GPI',
            'G006': 'Доставлен в банк получателя как не-GPI',
            'G007': 'Платеж переведен между MI агентами',
            'G008': 'Платеж переведен и получен MI агентами',
        }
        
        # Извлекаем основную информацию
        transaction_status = api_data.get('transactionStatus', 'UNKNOWN')
        status_info = status_mapping.get(transaction_status, {
            'status': transaction_status,
            'emoji': '❓',
            'description': 'Неизвестный статус'
        })
        
        # Извлекаем код причины
        reason_code = api_data.get('reasonCode', '')
        reason_description = reason_code_mapping.get(reason_code, api_data.get('statusDescription', ''))
        
        # Формируем ответ
        formatted_data = {
            'uetr': api_data.get('uetr', ''),
            'status': status_info['status'],
            'status_emoji': status_info['emoji'],
            'status_description': status_info['description'],
            'reason_code': reason_code,
            'reason_description': reason_description,
            'timestamp': api_data.get('timestamp', ''),
            'forward_bank_name': api_data.get('forwardBankName', ''),
            'forward_bank_code': api_data.get('forwardBankCode', ''),
            'remarks': api_data.get('remarks', ''),
            'raw_data': api_data
        }
        
        return formatted_data

    def _format_tracking_data(self, api_data):
        """Форматирование данных отслеживания от API"""
        
        # Извлекаем транзакции
        transactions = api_data.get('transactions', [])
        
        formatted_tracking = {
            'uetr': api_data.get('uetr', ''),
            'total_steps': len(transactions),
            'completed_steps': 0,
            'current_step': 0,
            'route': [],
            'estimated_completion': None,
            'raw_data': api_data
        }
        
        for i, transaction in enumerate(transactions):
            status = transaction.get('transactionStatus', '')
            
            # Считаем завершенные шаги
            if status in ['ACCC', 'ACSP']:
                formatted_tracking['completed_steps'] = i + 1
                formatted_tracking['current_step'] = i + 1
            
            # Формируем информацию о маршруте
            route_step = {
                'step': i + 1,
                'bank_name': transaction.get('agentName', ''),
                'bank_code': transaction.get('agentBIC', ''),
                'status': status,
                'timestamp': transaction.get('timestamp', ''),
                'reason_code': transaction.get('reasonCode', ''),
                'amount': transaction.get('instructedAmount', {}).get('amount', ''),
                'currency': transaction.get('instructedAmount', {}).get('currency', ''),
            }
            
            formatted_tracking['route'].append(route_step)
        
        return formatted_tracking 