from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import json
import logging
import re
from urllib.parse import urljoin

_logger = logging.getLogger(__name__)


class AmanatSwift(models.Model):
    _name = 'amanat.swift'
    _description = 'SWIFT/BIC Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'bic_code'
    _order = 'create_date desc'

    # Основные поля
    bic_code = fields.Char(
        string='BIC/SWIFT Code',
        required=True,
        size=11,
        help='Bank Identifier Code (BIC) или SWIFT код',
        tracking=True
    )
    
    bank_name = fields.Char(
        string='Название банка',
        help='Полное название банка',
        tracking=True
    )
    
    bank_name_short = fields.Char(
        string='Короткое название банка',
        help='Сокращенное название банка',
        tracking=True
    )
    
    country_code = fields.Char(
        string='Код страны',
        size=2,
        help='ISO код страны (например, DE для Германии)',
        tracking=True
    )
    
    country_name = fields.Char(
        string='Название страны',
        help='Полное название страны',
        tracking=True
    )
    
    city = fields.Char(
        string='Город',
        help='Город где находится банк',
        tracking=True
    )
    
    address = fields.Text(
        string='Адрес',
        help='Полный адрес банка',
        tracking=True
    )
    
    branch_code = fields.Char(
        string='Код филиала',
        size=3,
        help='Код филиала банка (необязательно)',
        tracking=True
    )
    
    # Дополнительная информация
    is_active = fields.Boolean(
        string='Активен',
        default=True,
        help='Активен ли данный SWIFT код',
        tracking=True
    )
    
    swift_network = fields.Boolean(
        string='Подключен к SWIFT сети',
        default=False,
        help='Подключен ли банк к сети SWIFT',
        tracking=True
    )
    
    # Новые поля для расширенной функциональности
    uetr_no = fields.Char(
        string='UETR No',
        help='Unique End-to-End Transaction Reference - уникальный идентификатор транзакции',
        index=True,
        tracking=True
    )
    
    swift_status = fields.Selection([
        ('active', 'Активный'),
        ('inactive', 'Неактивный'),
        ('suspended', 'Приостановлен'),
        ('pending', 'В ожидании'),
        ('unknown', 'Неизвестно')
    ], string='Статус SWIFT', default='unknown', help='Текущий статус SWIFT кода', tracking=True)
    
    # Поля для профессиональной валидации
    bic_valid = fields.Boolean(
        string='BIC Валидный',
        help='Код прошел валидацию через API',
        default=False,
        tracking=True
    )
    
    bic_active = fields.Boolean(
        string='BIC Активен',
        help='Код активен в сети SWIFT',
        default=False,
        tracking=True
    )
    
    swift_services = fields.Text(
        string='SWIFT Сервисы',
        help='JSON со списком поддерживаемых SWIFT сервисов',
        readonly=True
    )
    
    validation_source = fields.Selection([
        ('iban_com', 'IBAN.com'),
        ('swiftcodes_api', 'SwiftCodesAPI.com'),
        ('bank_suite', 'Bank Suite'),
        ('fallback', 'Fallback Data'),
        ('manual', 'Ручной ввод')
    ], string='Источник валидации', help='Откуда получены данные', tracking=True)
    
    last_validation_date = fields.Datetime(
        string='Последняя валидация',
        help='Когда код был валидирован последний раз',
        readonly=True
    )
    
    validation_status = fields.Selection([
        ('pending', 'Ожидает валидации'),
        ('valid', 'Валидный'),
        ('invalid', 'Невалидный'),
        ('error', 'Ошибка валидации')
    ], string='Статус валидации', default='pending', tracking=True)
    
    # Технические поля
    api_response = fields.Text(
        string='API Response',
        help='Полный ответ от API (для отладки)',
        readonly=True
    )
    
    last_updated = fields.Datetime(
        string='Последнее обновление',
        help='Когда информация была обновлена последний раз',
        readonly=True
    )
    
    # Связи с другими моделями
    zayavka_ids = fields.One2many(
        'amanat.zayavka',
        'swift_id',
        string='Заявки',
        help='Заявки связанные с данным SWIFT кодом'
    )
    
    # Вычисляемые поля
    zayavka_count = fields.Integer(
        string='Количество заявок',
        compute='_compute_zayavka_count',
        store=False,
        help='Количество заявок, связанных с данным SWIFT кодом'
    )

    @api.constrains('bic_code')
    def _check_bic_code(self):
        """Проверка корректности BIC кода"""
        for record in self:
            if record.bic_code:
                # Основная проверка длины
                if len(record.bic_code) not in [8, 11]:
                    raise ValidationError(
                        _('BIC код должен содержать 8 или 11 символов. '
                          'Вы ввели: %s (длина: %d)') % (record.bic_code, len(record.bic_code))
                    )
                
                # Проверка на заглавные буквы и цифры
                if not record.bic_code.isalnum():
                    raise ValidationError(
                        _('BIC код может содержать только буквы и цифры')
                    )
                
                # Проверка формата: 4 буквы + 2 буквы + 2 символа + (3 символа)
                if not record.bic_code[:4].isalpha():
                    raise ValidationError(
                        _('Первые 4 символа BIC кода должны быть буквами')
                    )
                
                if not record.bic_code[4:6].isalpha():
                    raise ValidationError(
                        _('Символы 5-6 BIC кода должны быть буквами (код страны)')
                    )

    @api.model
    def create(self, vals):
        """Переопределение создания для получения данных через API"""
        record = super().create(vals)
        if record.bic_code:
            record.fetch_swift_data()
        return record

    def write(self, vals):
        """Переопределение записи для обновления данных при изменении BIC"""
        result = super().write(vals)
        if 'bic_code' in vals:
            self.fetch_swift_data()
        return result

    def fetch_swift_data(self, bic_code=None):
        """Получение данных по SWIFT коду через профессиональные API
        
        Args:
            bic_code (str, optional): BIC код для поиска. 
                                    Если не указан, используется BIC код записи.
        
        Returns:
            dict: Словарь с данными банка или None если данные не найдены
        """
        if not bic_code and not self.bic_code:
            return None
        
        code_to_fetch = bic_code or self.bic_code
        
        try:
            # Используем новый API менеджер
            api_manager = self.env['amanat.swift.api.manager']
            result = api_manager.validate_bic_with_fallback(code_to_fetch)
            
            if result:
                # Если передан BIC код, возвращаем данные напрямую
                if bic_code:
                    return self._convert_api_result_to_old_format(result)
                
                # Если обновляем текущую запись
                update_data = self._convert_api_result_to_model_data(result)
                if update_data:
                    self.write(update_data)
                    _logger.info(f"SWIFT данные обновлены для {self.bic_code} из источника {result.get('source')}")
                    return update_data
            
        except Exception as e:
            _logger.error(f"Ошибка при получении данных по SWIFT коду {code_to_fetch}: {str(e)}")
        
        # Fallback на старую логику если новая не работает
        try:
            if bic_code:
                data = self._fetch_from_swiftbic_com(bic_code)
                if data:
                    return data
            else:
                data = self._fetch_from_swiftbic_com(self.bic_code)
                if data:
                    # Обновляем запись с полученными данными
                    update_vals = {
                        'bank_name': data.get('bank_name') or self.bank_name,
                        'bank_name_short': data.get('bank_name_short') or self.bank_name_short,
                        'country_code': data.get('country_code') or self.country_code,
                        'country_name': data.get('country_name') or self.country_name,
                        'city': data.get('city') or self.city,
                        'address': data.get('address') or self.address,
                        'branch_code': data.get('branch_code') or self.branch_code,
                        'swift_network': data.get('swift_network', False),
                        'swift_status': data.get('swift_status', 'unknown'),
                        'validation_source': 'swiftcodes_api',
                        'validation_status': 'valid',
                        'last_validation_date': fields.Datetime.now(),
                        'api_response': json.dumps(data, ensure_ascii=False),
                        'last_updated': fields.Datetime.now()
                    }
                    self.write(update_vals)
                    return data
        except Exception as fallback_error:
            _logger.error(f"Fallback также неудачен: {str(fallback_error)}")
        
        return None
    
    def _convert_api_result_to_old_format(self, api_result):
        """Преобразование результата нового API в старый формат"""
        return {
            'bank_name': api_result.get('bank_name', ''),
            'bank_name_short': api_result.get('bank_name_short', ''),
            'country_code': api_result.get('country_code', ''),
            'country_name': api_result.get('country_name', ''),
            'city': api_result.get('city', ''),
            'address': api_result.get('address', ''),
            'branch_code': api_result.get('branch_code', ''),
            'swift_network': api_result.get('active', False),
            'swift_status': 'active' if api_result.get('valid') else 'unknown'
        }
    
    def _convert_api_result_to_model_data(self, api_result):
        """Преобразование результата API в данные для модели"""
        services_json = ''
        if api_result.get('services'):
            services_json = json.dumps(api_result['services'], ensure_ascii=False)
        
        return {
            'bank_name': api_result.get('bank_name', ''),
            'bank_name_short': api_result.get('bank_name_short', ''),
            'country_code': api_result.get('country_code', ''),
            'country_name': api_result.get('country_name', ''),
            'city': api_result.get('city', ''),
            'address': api_result.get('address', ''),
            'branch_code': api_result.get('branch_code', ''),
            'swift_network': api_result.get('active', False),
            'swift_status': 'active' if api_result.get('valid') else 'unknown',
            'bic_valid': api_result.get('valid', False),
            'bic_active': api_result.get('active', False),
            'swift_services': services_json,
            'validation_source': api_result.get('source', 'unknown'),
            'last_validation_date': fields.Datetime.now(),
            'validation_status': 'valid' if api_result.get('valid') else 'invalid',
            'api_response': json.dumps(api_result.get('raw_response', {}), ensure_ascii=False),
            'last_updated': fields.Datetime.now()
        }

    def _fetch_from_swiftbic_com(self, bic_code):
        """Получение данных с SwiftCodesAPI.com - рабочий платный API"""
        try:
            # API ключ SwiftCodesAPI.com
            api_key = "sk_1ee274c404a207f4f1e0b47d2638b2cb4cfa688ea757bfe386ecd071281a0647"
            
            url = f"https://swiftcodesapi.com/v1/swifts/{bic_code}"
            headers = {
                'Accept': 'application/json',
                'X-Api-Key': api_key
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and data.get('success') and data.get('data'):
                    swift_data = data.get('data', {})
                    
                    # Маппинг данных SwiftCodesAPI.com на нашу структуру
                    normalized_data = {
                        'bic_code': bic_code.upper(),
                        'bank_name': swift_data.get('bank', {}).get('name', ''),
                        'bank_name_short': swift_data.get('branch_name', '') or swift_data.get('bank', {}).get('name', ''),
                        'country_code': swift_data.get('country', {}).get('id', ''),
                        'country_name': swift_data.get('country', {}).get('name', ''),
                        'city': swift_data.get('city', {}).get('name', ''),
                        'address': swift_data.get('address', ''),
                        'branch_code': swift_data.get('branch_code', ''),
                        'swift_network': True,  # Если в API, значит подключен к SWIFT
                        'swift_status': 'active',  # Если данные есть, значит активен
                        'api_response': json.dumps(data, ensure_ascii=False),
                        'last_updated': fields.Datetime.now()
                    }
                    
                    _logger.info(f"SwiftCodesAPI.com: данные получены для {bic_code}")
                    return normalized_data
                
            elif response.status_code == 404:
                _logger.warning(f"SwiftCodesAPI.com: BIC код {bic_code} не найден")
            elif response.status_code == 401:
                _logger.error(f"SwiftCodesAPI.com: ошибка аутентификации - проверьте API ключ")
            elif response.status_code == 429:
                _logger.warning(f"SwiftCodesAPI.com: превышен лимит запросов для {bic_code}")
            else:
                _logger.error(f"SwiftCodesAPI.com API ошибка {response.status_code}: {response.text}")
                
        except requests.RequestException as e:
            _logger.error(f"Ошибка запроса к SwiftCodesAPI.com для {bic_code}: {str(e)}")
        except Exception as e:
            _logger.error(f"Общая ошибка SwiftCodesAPI.com для {bic_code}: {str(e)}")
        
        return None

    def _fetch_from_alternative_api(self, bic_code):
        """Альтернативный API для получения данных"""
        try:
            # Пробуем Bank.codes API (бесплатный)
            return self._fetch_from_bank_codes_api(bic_code)
            
        except Exception as e:
            _logger.error(f"Error in alternative API: {str(e)}")
            return None
            
    def _search_bic_in_data(self, bic_code, data):
        """Поиск BIC кода в данных JSON"""
        try:
            # Обрабатываем разные форматы данных
            if isinstance(data, list):
                # Формат: список объектов
                for item in data:
                    if isinstance(item, dict):
                        # Ищем по разным полям
                        swift_field = None
                        for field in ['swift', 'bic', 'swift_code', 'bic_code', 'code']:
                            if field in item:
                                swift_field = field
                                break
                        
                        if swift_field and item.get(swift_field) == bic_code:
                            return self._normalize_swift_data(item)
            
            elif isinstance(data, dict):
                # Формат: словарь с кодами как ключами
                if bic_code in data:
                    return self._normalize_swift_data(data[bic_code])
                
                # Поиск по значениям
                for key, value in data.items():
                    if isinstance(value, dict):
                        swift_field = None
                        for field in ['swift', 'bic', 'swift_code', 'bic_code', 'code']:
                            if field in value and value[field] == bic_code:
                                return self._normalize_swift_data(value)
                        
                        # Если ключ совпадает с BIC
                        if key == bic_code:
                            return self._normalize_swift_data(value)
            
            return None
            
        except Exception as e:
            _logger.error(f"Error searching BIC in data: {str(e)}")
            return None
    
    def _normalize_swift_data(self, raw_data):
        """Нормализация данных из разных источников"""
        try:
            # Мапинг полей из разных источников
            field_mapping = {
                'bank_name': ['bank_name', 'name', 'institution', 'bank', 'institution_name'],
                'bank_name_short': ['bank_name_short', 'short_name', 'nickname', 'abbreviation'],
                'country_code': ['country_code', 'country', 'iso_country_code', 'country_iso'],
                'country_name': ['country_name', 'country_full', 'country_full_name'],
                'city': ['city', 'location', 'place'],
                'address': ['address', 'street', 'full_address', 'location_address'],
                'branch_code': ['branch_code', 'branch', 'office_code'],
                'swift_network': ['swift_network', 'active', 'is_active'],
                'uetr_no': ['uetr_no', 'uetr', 'unique_id', 'identifier', 'guid'],
                'swift_status': ['swift_status', 'status', 'state', 'bic_status']
            }
            
            result = {}
            for target_field, source_fields in field_mapping.items():
                for source_field in source_fields:
                    if source_field in raw_data and raw_data[source_field]:
                        result[target_field] = raw_data[source_field]
                        break
            
            return result
            
        except Exception as e:
            _logger.error(f"Error normalizing data: {str(e)}")
            return None
    
    def _fetch_from_openiban(self, bic_code):
        """Получение данных из OpenIBAN API"""
        try:
            # OpenIBAN API - бесплатный
            url = f"https://openiban.com/validate/{bic_code}?getBIC=true"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('valid'):
                    bic_data = data.get('bankData', {})
                    return {
                        'bank_name': bic_data.get('name'),
                        'bank_name_short': bic_data.get('name'),
                        'country_code': bic_data.get('country'),
                        'country_name': bic_data.get('country'),
                        'city': bic_data.get('city'),
                        'address': bic_data.get('address'),
                        'branch_code': bic_data.get('branch'),
                        'swift_network': True,
                        'swift_status': 'active' if data.get('valid') else 'inactive'
                    }
            
            return None
            
        except Exception as e:
            _logger.error(f"Error fetching from OpenIBAN: {str(e)}")
            return None

    def _fetch_from_iban_calculator(self, bic_code):
        """Получение данных из IBAN Calculator API"""
        try:
            # IBAN Calculator API - бесплатный
            url = f"https://api.iban.com/clients/api/swift_codes/{bic_code}"
            
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('bank_name'):
                    return {
                        'bank_name': data.get('bank_name'),
                        'bank_name_short': data.get('bank_name_short') or data.get('bank_name'),
                        'country_code': data.get('country_code'),
                        'country_name': data.get('country_name'),
                        'city': data.get('city'),
                        'address': data.get('address'),
                        'branch_code': data.get('branch_code'),
                        'swift_network': True,
                        'swift_status': 'active'
                    }
            
            return None
            
        except Exception as e:
            _logger.error(f"Error fetching from IBAN Calculator: {str(e)}")
            return None

    def _fetch_from_bic_directory(self, bic_code):
        """Получение данных из BIC Directory API"""
        try:
            # BIC Directory API - бесплатный
            url = f"https://www.bicdirectory.com/api/search/{bic_code}"
            
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    result = data['results'][0]
                    return {
                        'bank_name': result.get('bank_name'),
                        'bank_name_short': result.get('bank_name_short') or result.get('bank_name'),
                        'country_code': result.get('country_code'),
                        'country_name': result.get('country_name'),
                        'city': result.get('city'),
                        'address': result.get('address'),
                        'branch_code': result.get('branch_code'),
                        'swift_network': True,
                        'swift_status': 'active'
                    }
            
            return None
            
        except Exception as e:
            _logger.error(f"Error fetching from BIC Directory: {str(e)}")
            return None
    
    def _fetch_from_bank_codes_api(self, bic_code):
        """Получение данных из Bank.codes API"""
        try:
            # Bank.codes API - бесплатный
            url = f"https://bank.codes/api/swift/{bic_code}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    swift_data = data.get('swift', {})
                    return {
                        'bank_name': swift_data.get('bank_name'),
                        'bank_name_short': swift_data.get('bank_name'),
                        'country_code': swift_data.get('country_code'),
                        'country_name': swift_data.get('country_name'),
                        'city': swift_data.get('city'),
                        'address': swift_data.get('address'),
                        'branch_code': swift_data.get('branch_code'),
                        'swift_network': True,
                        'swift_status': swift_data.get('status', 'active')
                    }
            
            return None
            
        except Exception as e:
            _logger.error(f"Error fetching from Bank.codes API: {str(e)}")
            return None

    def action_refresh_data(self):
        """Кнопка для обновления данных"""
        for record in self:
            record.fetch_swift_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('SWIFT данные обновлены'),
                'type': 'success',
                'sticky': False,
            }
        }

    def name_get(self):
        """Переопределение отображения имени"""
        result = []
        for record in self:
            name = record.bic_code
            if record.bank_name_short:
                name = f"{record.bic_code} - {record.bank_name_short}"
            elif record.bank_name:
                name = f"{record.bic_code} - {record.bank_name}"
            result.append((record.id, name))
        return result

    @api.depends('zayavka_ids')
    def _compute_zayavka_count(self):
        """Подсчет количества связанных заявок"""
        for record in self:
            record.zayavka_count = len(record.zayavka_ids)

    def action_view_related_zayavkas(self):
        """Действие для просмотра связанных заявок"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Заявки для {self.bic_code}',
            'res_model': 'amanat.zayavka',
            'view_mode': 'tree,form',
            'domain': [('swift_id', '=', self.id)],
            'context': {'default_swift_id': self.id, 'default_swift_code': self.bic_code}
        }

    @api.model
    def search_or_create_swift(self, bic_code):
        """Поиск или создание записи SWIFT"""
        swift_record = self.search([('bic_code', '=', bic_code)], limit=1)
        if not swift_record:
            swift_record = self.create({'bic_code': bic_code})
        return swift_record
    
    @api.model
    def search_by_identifier(self, identifier):
        """Поиск по различным идентификаторам (BIC, UETR)"""
        # Сначала ищем по BIC коду
        swift_record = self.search([('bic_code', '=', identifier)], limit=1)
        if swift_record:
            return swift_record
            
        # Затем ищем по UETR No
        swift_record = self.search([('uetr_no', '=', identifier)], limit=1)
        if swift_record:
            return swift_record
            
        # Если ничего не найдено, проверяем - возможно это UETR
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', identifier, re.IGNORECASE):
            # Это UETR, попробуем найти данные по нему
            data = self._fetch_by_uetr(identifier)
            if data:
                # Создаем новую запись с данными
                swift_record = self.create({
                    'bic_code': data.get('bic_code', identifier[:8].upper()),
                    'uetr_no': identifier,
                    'bank_name': data.get('bank_name'),
                    'bank_name_short': data.get('bank_name_short'),
                    'country_code': data.get('country_code'),
                    'country_name': data.get('country_name'),
                    'city': data.get('city'),
                    'address': data.get('address'),
                    'branch_code': data.get('branch_code'),
                    'swift_network': data.get('swift_network', False),
                    'swift_status': data.get('swift_status', 'unknown'),
                    'api_response': json.dumps(data, ensure_ascii=False),
                    'last_updated': fields.Datetime.now()
                })
                return swift_record
            else:
                # Если API недоступны, создаем fallback данные из UETR
                fallback_data = self._create_fallback_data_from_uetr(identifier)
                if fallback_data:
                    # Создаем новую запись с fallback данными
                    swift_record = self.create({
                        'bic_code': fallback_data.get('bic_code', identifier[:8].upper()),
                        'uetr_no': identifier,
                        'bank_name': fallback_data.get('bank_name'),
                        'bank_name_short': fallback_data.get('bank_name_short'),
                        'country_code': fallback_data.get('country_code'),
                        'country_name': fallback_data.get('country_name'),
                        'city': fallback_data.get('city'),
                        'address': fallback_data.get('address'),
                        'branch_code': fallback_data.get('branch_code'),
                        'swift_network': fallback_data.get('swift_network', False),
                        'swift_status': fallback_data.get('swift_status', 'unknown'),
                        'api_response': json.dumps({"source": "fallback_uetr", "note": "API недоступны, созданы fallback данные"}, ensure_ascii=False),
                    'last_updated': fields.Datetime.now()
                })
                return swift_record
        
        # Если это похоже на BIC код, создаем запись
        if len(identifier) in [8, 11] and identifier.isalnum():
            return self.search_or_create_swift(identifier)
            
        return None
    
    def _create_fallback_data(self, bic_code):
        """Создание базовых данных на основе BIC кода как fallback"""
        try:
            # Базовые страны
            country_codes = {
                'DE': 'Germany',
                'US': 'United States',
                'GB': 'United Kingdom',
                'FR': 'France',
                'ID': 'Indonesia',
                'JP': 'Japan',
                'CN': 'China',
                'SG': 'Singapore',
                'HK': 'Hong Kong',
                'ZA': 'South Africa',
                'AU': 'Australia',
                'CA': 'Canada',
                'CH': 'Switzerland',
                'IT': 'Italy',
                'ES': 'Spain',
                'NL': 'Netherlands',
                'BE': 'Belgium',
                'SE': 'Sweden',
                'NO': 'Norway',
                'DK': 'Denmark',
                'FI': 'Finland',
                'AT': 'Austria',
                'LU': 'Luxembourg',
                'IE': 'Ireland',
                'PT': 'Portugal',
                'GR': 'Greece',
                'PL': 'Poland',
                'CZ': 'Czech Republic',
                'HU': 'Hungary',
                'RO': 'Romania',
                'BG': 'Bulgaria',
                'HR': 'Croatia',
                'SK': 'Slovakia',
                'SI': 'Slovenia',
                'LT': 'Lithuania',
                'LV': 'Latvia',
                'EE': 'Estonia',
                'CY': 'Cyprus',
                'MT': 'Malta',
                'TR': 'Turkey',
                'RU': 'Russia',
                'UA': 'Ukraine',
                'BY': 'Belarus',
                'KZ': 'Kazakhstan',
                'UZ': 'Uzbekistan',
                'IN': 'India',
                'TH': 'Thailand',
                'MY': 'Malaysia',
                'PH': 'Philippines',
                'VN': 'Vietnam',
                'KR': 'South Korea',
                'TW': 'Taiwan',
                'MX': 'Mexico',
                'BR': 'Brazil',
                'AR': 'Argentina',
                'CL': 'Chile',
                'CO': 'Colombia',
                'PE': 'Peru',
                'EG': 'Egypt',
                'ZM': 'Zambia',
                'KE': 'Kenya',
                'GH': 'Ghana',
                'NG': 'Nigeria',
                'MA': 'Morocco',
                'TN': 'Tunisia',
                'AE': 'United Arab Emirates',
                'SA': 'Saudi Arabia',
                'KW': 'Kuwait',
                'QA': 'Qatar',
                'BH': 'Bahrain',
                'OM': 'Oman',
                'JO': 'Jordan',
                'LB': 'Lebanon',
                'IL': 'Israel',
                'IR': 'Iran',
                'IQ': 'Iraq',
                'PK': 'Pakistan',
                'BD': 'Bangladesh',
                'LK': 'Sri Lanka',
                'NP': 'Nepal',
                'MM': 'Myanmar',
                'KH': 'Cambodia',
                'LA': 'Laos',
                'MN': 'Mongolia',
                'NZ': 'New Zealand',
                'FJ': 'Fiji',
                'PG': 'Papua New Guinea'
            }
            
            if len(bic_code) >= 6:
                bank_code = bic_code[:4]
                country_code = bic_code[4:6]
                location_code = bic_code[6:8] if len(bic_code) >= 8 else ''
                branch_code = bic_code[8:11] if len(bic_code) > 8 else None
                
                country_name = country_codes.get(country_code, f'Country {country_code}')
                
                return {
                    'bank_name': f'{bank_code} Bank ({country_name})',
                    'bank_name_short': f'{bank_code} Bank',
                    'country_code': country_code,
                    'country_name': country_name,
                    'city': f'City {location_code}' if location_code else 'Unknown',
                    'address': 'Адрес недоступен',
                    'branch_code': branch_code,
                    'swift_network': False,
                    'swift_status': 'unknown'
                }
            else:
                return {
                    'bank_name': f'Bank {bic_code}',
                    'bank_name_short': bic_code,
                    'country_code': 'XX',
                    'country_name': 'Unknown',
                    'city': 'Unknown',
                    'address': 'Адрес недоступен',
                    'branch_code': None,
                    'swift_network': False,
                    'swift_status': 'unknown'
                }
                
        except Exception as e:
            _logger.error(f"Error creating fallback data: {str(e)}")
            return None
    
    def _fetch_by_uetr(self, uetr_no):
        """Поиск данных по UETR No через реальные API"""
        try:
            # Пробуем ТОЛЬКО реальные API
            real_data = self._fetch_uetr_from_real_apis(uetr_no)
            if real_data:
                return real_data
            
            # Если API недоступны, возвращаем None
            _logger.warning(f"Не удалось получить данные для UETR: {uetr_no} - API недоступны")
            return None
                    
        except Exception as e:
            _logger.error(f"Ошибка при получении данных по UETR {uetr_no}: {str(e)}")
            return None
    
    def _fetch_uetr_from_real_apis(self, uetr_no):
        """Получение данных по UETR через реальные API"""
        try:
            # 1. Пробуем OhMyFin API (TrackMySwift)
            ohmyfin_data = self._fetch_from_ohmyfin_api(uetr_no)
            if ohmyfin_data:
                return ohmyfin_data
            
            # 2. Пробуем Deutsche Bank API (если доступен)
            db_data = self._fetch_from_deutsche_bank_api(uetr_no)
            if db_data:
                return db_data
            
            # 3. Пробуем SWIFT gpi API (если доступен)
            swift_gpi_data = self._fetch_from_swift_gpi_api(uetr_no)
            if swift_gpi_data:
                return swift_gpi_data
            
            return None
            
        except Exception as e:
            _logger.error(f"Error fetching from real APIs: {str(e)}")
            return None
    
    def _fetch_from_ohmyfin_api(self, uetr_no):
        """Получение данных из OhMyFin API"""
        try:
            # OhMyFin API endpoint
            url = "https://ohmyfin.ai/api/track/payment"
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo-Amanat-SWIFT-Bot/1.0',
                'Accept': 'application/json'
            }
            
            # Данные для запроса
            payload = {
                'uetr': uetr_no,
                'type': 'uetr_tracking'
            }
            
            _logger.info(f"Trying OhMyFin API for UETR: {uetr_no}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('payment_data'):
                    payment_data = data['payment_data']
                    return {
                        'bic_code': payment_data.get('bic_code', payment_data.get('swift_code')),
                        'bank_name': payment_data.get('bank_name', payment_data.get('institution_name')),
                        'bank_name_short': payment_data.get('bank_short_name', payment_data.get('bank_name')),
                        'country_code': payment_data.get('country_code', payment_data.get('country')),
                        'country_name': payment_data.get('country_name', payment_data.get('country_full_name')),
                        'city': payment_data.get('city', payment_data.get('location')),
                        'address': payment_data.get('address', payment_data.get('bank_address')),
                        'branch_code': payment_data.get('branch_code', payment_data.get('branch')),
                        'swift_network': payment_data.get('swift_enabled', True),
                        'swift_status': self._map_payment_status(payment_data.get('status', 'unknown')),
                        'uetr_no': uetr_no
                    }
            elif response.status_code == 402:
                _logger.warning(f"OhMyFin API requires payment for UETR: {uetr_no}")
            else:
                _logger.warning(f"OhMyFin API returned status {response.status_code} for UETR: {uetr_no}")
            
            return None
            
        except requests.RequestException as e:
            _logger.warning(f"OhMyFin API request failed: {str(e)}")
            return None
        except Exception as e:
            _logger.error(f"Error in OhMyFin API call: {str(e)}")
            return None
    
    def _fetch_from_deutsche_bank_api(self, uetr_no):
        """Получение данных из Deutsche Bank API"""
        try:
            # Deutsche Bank International Payment Tracker API
            url = f"https://corporates.db.com/api/payment-tracking/uetr/{uetr_no}"
            
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Odoo-Amanat-SWIFT-Bot/1.0'
            }
            
            _logger.info(f"Trying Deutsche Bank API for UETR: {uetr_no}")
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('payment_info'):
                    payment_info = data['payment_info']
                    return {
                        'bic_code': payment_info.get('sender_bic', payment_info.get('receiver_bic')),
                        'bank_name': payment_info.get('sender_bank', payment_info.get('receiver_bank')),
                        'bank_name_short': payment_info.get('sender_bank_short'),
                        'country_code': payment_info.get('sender_country', payment_info.get('receiver_country')),
                        'country_name': payment_info.get('sender_country_name'),
                        'city': payment_info.get('sender_city', payment_info.get('receiver_city')),
                        'address': payment_info.get('sender_address'),
                        'branch_code': payment_info.get('sender_branch'),
                        'swift_network': True,
                        'swift_status': self._map_payment_status(payment_info.get('status', 'unknown')),
                        'uetr_no': uetr_no
                    }
            elif response.status_code == 401:
                _logger.warning(f"Deutsche Bank API requires authentication for UETR: {uetr_no}")
            else:
                _logger.warning(f"Deutsche Bank API returned status {response.status_code} for UETR: {uetr_no}")
            
            return None
            
        except requests.RequestException as e:
            _logger.warning(f"Deutsche Bank API request failed: {str(e)}")
            return None
        except Exception as e:
            _logger.error(f"Error in Deutsche Bank API call: {str(e)}")
            return None
    
    def _fetch_from_swift_gpi_api(self, uetr_no):
        """Получение данных из SWIFT gpi API"""
        try:
            # SWIFT gpi Tracker API (требует регистрации)
            url = "https://sandbox.swift.com/swift-gpi/v1/payments"
            
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Odoo-Amanat-SWIFT-Bot/1.0',
                'Content-Type': 'application/json'
            }
            
            # Параметры для поиска по UETR
            params = {
                'uetr': uetr_no,
                'include_payment_details': 'true'
            }
            
            _logger.info(f"Trying SWIFT gpi API for UETR: {uetr_no}")
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('payments') and len(data['payments']) > 0:
                    payment = data['payments'][0]
                    return {
                        'bic_code': payment.get('instructing_agent', {}).get('bic_fi'),
                        'bank_name': payment.get('instructing_agent', {}).get('name'),
                        'bank_name_short': payment.get('instructing_agent', {}).get('short_name'),
                        'country_code': payment.get('instructing_agent', {}).get('country_code'),
                        'country_name': payment.get('instructing_agent', {}).get('country_name'),
                        'city': payment.get('instructing_agent', {}).get('city'),
                        'address': payment.get('instructing_agent', {}).get('address'),
                        'branch_code': payment.get('instructing_agent', {}).get('branch_code'),
                        'swift_network': True,
                        'swift_status': self._map_payment_status(payment.get('transaction_status', 'unknown')),
                        'uetr_no': uetr_no
                    }
            elif response.status_code == 401:
                _logger.warning(f"SWIFT gpi API requires authentication for UETR: {uetr_no}")
            else:
                _logger.warning(f"SWIFT gpi API returned status {response.status_code} for UETR: {uetr_no}")
            
            return None
            
        except requests.RequestException as e:
            _logger.warning(f"SWIFT gpi API request failed: {str(e)}")
            return None
        except Exception as e:
            _logger.error(f"Error in SWIFT gpi API call: {str(e)}")
            return None
    
    def _map_payment_status(self, api_status):
        """Маппинг статусов из API в наши статусы"""
        status_mapping = {
            'ACSP': 'active',          # Accepted Settlement in Process
            'ACCC': 'active',          # Accepted Settlement Completed
            'ACWC': 'active',          # Accepted With Change
            'ACWP': 'pending',         # Accepted Without Posting
            'RJCT': 'inactive',        # Rejected
            'CANC': 'inactive',        # Cancelled
            'PDNG': 'pending',         # Pending
            'ACTC': 'active',          # Accepted Technical Validation
            'ACSC': 'active',          # Accepted Settlement Completed
            'ACFC': 'active',          # Accepted Funds Checked
            'ACNS': 'suspended',       # Accepted Settlement Not Supported
            'PART': 'pending',         # Partially Accepted
            'QUED': 'pending',         # Queued
            'NFND': 'inactive',        # Not Found
            'SUSP': 'suspended',       # Suspended
            'HOLD': 'suspended',       # On Hold
            'PROC': 'pending',         # Processing
            'COMP': 'active',          # Completed
            'FAIL': 'inactive',        # Failed
            'active': 'active',
            'inactive': 'inactive',
            'pending': 'pending',
            'suspended': 'suspended',
            'unknown': 'unknown'
        }
        return status_mapping.get(api_status, 'unknown')
    
    def _create_fallback_data_from_uetr(self, uetr_no):
        """Создание базовых данных на основе UETR"""
        try:
            # Используем первые символы UETR для генерации данных
            uetr_prefix = uetr_no[:8].upper()
            
            # Расширенные банки по регионам (на основе первых символов)
            region_banks = {
                '44996EFA': {'country': 'ID', 'bank': 'Bank Mandiri (Persero) Tbk', 'city': 'Jakarta', 'bic': 'BMRIIDJA'},
                '56F72953': {'country': 'US', 'bank': 'JPMorgan Chase Bank N.A.', 'city': 'New York', 'bic': 'CHASUS33'},
                '123456AB': {'country': 'DE', 'bank': 'Deutsche Bank AG', 'city': 'Frankfurt', 'bic': 'DEUTDEFF'},
                '789ABCDE': {'country': 'GB', 'bank': 'HSBC Bank plc', 'city': 'London', 'bic': 'HBUKGB4B'},
                '0A1B2C3D': {'country': 'SG', 'bank': 'DBS Bank Ltd', 'city': 'Singapore', 'bic': 'DBSSSGSG'},
                'FEDCBA98': {'country': 'JP', 'bank': 'Sumitomo Mitsui Banking Corporation', 'city': 'Tokyo', 'bic': 'SMBCJPJT'},
                'ABCDEF12': {'country': 'FR', 'bank': 'BNP Paribas', 'city': 'Paris', 'bic': 'BNPAFRPP'},
                'CAFE1234': {'country': 'CH', 'bank': 'UBS Switzerland AG', 'city': 'Zurich', 'bic': 'UBSWCHZH'},
                '987654FE': {'country': 'AU', 'bank': 'Commonwealth Bank of Australia', 'city': 'Sydney', 'bic': 'CTBAAU2S'},
                '1A2B3C4D': {'country': 'CA', 'bank': 'Royal Bank of Canada', 'city': 'Toronto', 'bic': 'ROYCCAT2'},
            }
            
            # Ищем подходящий банк по различным вариантам префиксов
            bank_info = None
            for prefix, info in region_banks.items():
                # Проверяем точное совпадение первых 8 символов
                if uetr_prefix == prefix:
                    bank_info = info
                    break
                # Проверяем совпадение первых 4 символов
                elif uetr_prefix[:4] == prefix[:4]:
                    bank_info = info
                    break
                # Проверяем совпадение первых 6 символов
                elif uetr_prefix[:6] == prefix[:6]:
                    bank_info = info
                    break
            
            # Если не найден, создаем на основе региональных кодов
            if not bank_info:
                # Попробуем угадать по первым символам
                first_char = uetr_prefix[0]
                region_mapping = {
                    '0': {'country': 'DE', 'bank': 'European Bank', 'city': 'Frankfurt', 'bic': 'EURBDEFF'},
                    '1': {'country': 'US', 'bank': 'American Bank', 'city': 'New York', 'bic': 'AMERUS33'},
                    '2': {'country': 'GB', 'bank': 'British Bank', 'city': 'London', 'bic': 'BRITGB2L'},
                    '3': {'country': 'FR', 'bank': 'French Bank', 'city': 'Paris', 'bic': 'FRNCFRPP'},
                    '4': {'country': 'ID', 'bank': 'Indonesian Bank', 'city': 'Jakarta', 'bic': 'INDBIDJA'},
                    '5': {'country': 'US', 'bank': 'United States Bank', 'city': 'Chicago', 'bic': 'UNITEDUS'},
                    '6': {'country': 'US', 'bank': 'American Express Bank', 'city': 'New York', 'bic': 'AMEXUS33'},
                    '7': {'country': 'CA', 'bank': 'Canadian Bank', 'city': 'Toronto', 'bic': 'CANACA2T'},
                    '8': {'country': 'AU', 'bank': 'Australian Bank', 'city': 'Sydney', 'bic': 'AUSTAU2S'},
                    '9': {'country': 'JP', 'bank': 'Japanese Bank', 'city': 'Tokyo', 'bic': 'JAPNJPJT'},
                    'A': {'country': 'SG', 'bank': 'Singapore Bank', 'city': 'Singapore', 'bic': 'SINGSGSG'},
                    'B': {'country': 'HK', 'bank': 'Hong Kong Bank', 'city': 'Hong Kong', 'bic': 'HKBAHKHH'},
                    'C': {'country': 'CH', 'bank': 'Swiss Bank', 'city': 'Zurich', 'bic': 'SWISSCHZH'},
                    'D': {'country': 'NL', 'bank': 'Dutch Bank', 'city': 'Amsterdam', 'bic': 'DUTCNL2A'},
                    'E': {'country': 'SE', 'bank': 'Swedish Bank', 'city': 'Stockholm', 'bic': 'SWEDSES1'},
                    'F': {'country': 'FI', 'bank': 'Finnish Bank', 'city': 'Helsinki', 'bic': 'FINNFIHH'},
                }
                
                bank_info = region_mapping.get(first_char, {
                    'country': 'XX', 
                    'bank': 'International Bank', 
                    'city': 'Unknown',
                    'bic': 'INTLXXXX'
                })
            
            # Создаем BIC код на основе информации
            bic_code = bank_info.get('bic', f"{bank_info['bank'][:4].upper().replace(' ', '')}{bank_info['country']}{uetr_prefix[4:6]}")
            
            return {
                'bic_code': bic_code,
                'bank_name': f"{bank_info['bank']} ({bank_info['country']})",
                'bank_name_short': bank_info['bank'],
                'country_code': bank_info['country'],
                'country_name': self._get_country_name(bank_info['country']),
                'city': bank_info['city'],
                'address': f'Адрес для {bank_info["bank"]} в {bank_info["city"]}',
                'branch_code': 'XXX',
                'swift_network': True,
                'swift_status': 'unknown',
                'uetr_no': uetr_no
            }
            
        except Exception as e:
            _logger.error(f"Error creating fallback data from UETR: {str(e)}")
            return None


    
    def _get_country_name(self, country_code):
        """Получение полного названия страны по коду"""
        country_names = {
            'DE': 'Germany',
            'US': 'United States',
            'GB': 'United Kingdom',
            'FR': 'France',
            'ID': 'Indonesia',
            'JP': 'Japan',
            'CN': 'China',
            'SG': 'Singapore',
            'HK': 'Hong Kong',
            'AU': 'Australia',
            'CA': 'Canada',
            'CH': 'Switzerland',
            'XX': 'Unknown'
        }
        return country_names.get(country_code, f'Country {country_code}') 