from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SwiftApiConfig(models.Model):
    _name = 'amanat.swift.api.config'
    _description = 'Swift GPI API Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Название конфигурации',
        required=True,
        default='Swift GPI API Config'
    )
    
    # API настройки
    api_base_url = fields.Char(
        string='API Base URL',
        required=True,
        default='https://sandbox.swift.com/swift-apitracker-pilot/v4',
        help='Базовый URL для Swift GPI API (sandbox или production)'
    )
    
    consumer_key = fields.Char(
        string='Consumer Key',
        required=True,
        help='Consumer Key полученный из Swift Developer Portal'
    )
    
    consumer_secret = fields.Char(
        string='Consumer Secret',
        required=True,
        help='Consumer Secret полученный из Swift Developer Portal'
    )
    
    # OAuth настройки
    oauth_url = fields.Char(
        string='OAuth URL',
        required=True,
        default='https://sandbox.swift.com/oauth2/v1/token',
        help='URL для получения OAuth токена'
    )
    
    # Сертификаты и безопасность
    use_client_certificate = fields.Boolean(
        string='Использовать клиентский сертификат',
        default=True,
        help='Использовать клиентский сертификат для аутентификации'
    )
    
    certificate_path = fields.Char(
        string='Путь к сертификату',
        help='Путь к клиентскому сертификату (.pem файл)'
    )
    
    private_key_path = fields.Char(
        string='Путь к приватному ключу',
        help='Путь к приватному ключу (.key файл)'
    )
    
    # Настройки запросов
    timeout = fields.Integer(
        string='Timeout (секунды)',
        default=30,
        help='Таймаут для API запросов'
    )
    
    max_retries = fields.Integer(
        string='Максимум повторов',
        default=3,
        help='Максимальное количество повторов при ошибке'
    )
    
    # Статус
    is_active = fields.Boolean(
        string='Активна',
        default=True,
        help='Активна ли данная конфигурация'
    )
    
    is_sandbox = fields.Boolean(
        string='Sandbox режим',
        default=True,
        help='Использовать sandbox API вместо production'
    )
    
    # Мониторинг
    last_successful_call = fields.Datetime(
        string='Последний успешный вызов',
        readonly=True,
        help='Когда последний раз API ответил успешно'
    )
    
    total_calls = fields.Integer(
        string='Всего вызовов',
        default=0,
        readonly=True,
        help='Общее количество API вызовов'
    )
    
    successful_calls = fields.Integer(
        string='Успешных вызовов',
        default=0,
        readonly=True,
        help='Количество успешных API вызовов'
    )
    
    failed_calls = fields.Integer(
        string='Неудачных вызовов',
        default=0,
        readonly=True,
        help='Количество неудачных API вызовов'
    )
    
    success_rate = fields.Float(
        string='Процент успешных вызовов',
        compute='_compute_success_rate',
        store=False,
        help='Процент успешных API вызовов'
    )

    @api.depends('total_calls', 'successful_calls')
    def _compute_success_rate(self):
        """Вычисление процента успешных вызовов"""
        for record in self:
            if record.total_calls > 0:
                record.success_rate = (record.successful_calls / record.total_calls) * 100
            else:
                record.success_rate = 0.0

    @api.constrains('consumer_key', 'consumer_secret')
    def _check_credentials(self):
        """Валидация API credentials"""
        for record in self:
            if record.consumer_key and len(record.consumer_key) < 10:
                raise ValidationError(_('Consumer Key слишком короткий'))
            if record.consumer_secret and len(record.consumer_secret) < 10:
                raise ValidationError(_('Consumer Secret слишком короткий'))

    def action_test_connection(self):
        """Тест подключения к Swift GPI API"""
        self.ensure_one()
        
        try:
            # Тестируем получение OAuth токена
            from .swift_gpi_client import SwiftGpiClient
            
            client = SwiftGpiClient(self)
            token = client.get_oauth_token()
            
            if token:
                self.last_successful_call = fields.Datetime.now()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('✅ Подключение к Swift GPI API успешно!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('❌ Не удалось получить OAuth токен'),
                        'type': 'error',
                        'sticky': True,
                    }
                }
                
        except Exception as e:
            _logger.error(f"Swift GPI API connection test failed: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('❌ Ошибка подключения: %s') % str(e),
                    'type': 'error',
                    'sticky': True,
                }
            }

    def record_api_call(self, success=True):
        """Записать статистику API вызова"""
        self.total_calls += 1
        if success:
            self.successful_calls += 1
            self.last_successful_call = fields.Datetime.now()
        else:
            self.failed_calls += 1

    @api.model
    def get_active_config(self):
        """Получить активную конфигурацию API"""
        config = self.search([('is_active', '=', True)], limit=1)
        if not config:
            raise UserError(_(
                'Не найдена активная конфигурация Swift GPI API. '
                'Пожалуйста, создайте и настройте конфигурацию в меню SWIFT → Настройки API.'
            ))
        return config

    def name_get(self):
        """Отображение имени конфигурации"""
        result = []
        for record in self:
            name = f"{record.name}"
            if record.is_sandbox:
                name += " (Sandbox)"
            if not record.is_active:
                name += " (Неактивна)"
            result.append((record.id, name))
        return result 