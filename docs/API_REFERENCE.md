# 🔌 API Reference - Техническая документация

## 📋 Содержание

1. [Модель amanat.swift](#модель-amanatswift)
2. [Основные методы](#основные-методы)
3. [API интеграции](#api-интеграции)
4. [Валидация данных](#валидация-данных)
5. [Обработка ошибок](#обработка-ошибок)
6. [Примеры кода](#примеры-кода)

---

## 📊 Модель amanat.swift

### Наследование
```python
class AmanatSwift(models.Model):
    _name = 'amanat.swift'
    _description = 'SWIFT/BIC Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'bic_code'
    _order = 'create_date desc'
```

### Поля модели

#### Основные поля
```python
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
```

#### Дополнительные поля
```python
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

uetr_no = fields.Char(
    string='UETR No',
    help='Unique End-to-End Transaction Reference',
    index=True,
    tracking=True
)

swift_status = fields.Selection([
    ('active', 'Активный'),
    ('inactive', 'Неактивный'),
    ('suspended', 'Приостановлен'),
    ('pending', 'В ожидании'),
    ('unknown', 'Неизвестно')
], string='Статус SWIFT', default='unknown', tracking=True)
```

#### Технические поля
```python
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
```

#### Связи
```python
zayavka_ids = fields.One2many(
    'amanat.zayavka',
    'swift_id',
    string='Заявки',
    help='Заявки связанные с данным SWIFT кодом'
)

zayavka_count = fields.Integer(
    string='Количество заявок',
    compute='_compute_zayavka_count',
    store=False
)
```

---

## 🛠️ Основные методы

### create()
```python
@api.model
def create(self, vals):
    """Переопределение создания для получения данных через API"""
    record = super().create(vals)
    if record.bic_code:
        record.fetch_swift_data()
    return record
```

### write()
```python
def write(self, vals):
    """Переопределение записи для обновления данных при изменении BIC"""
    result = super().write(vals)
    if 'bic_code' in vals:
        self.fetch_swift_data()
    return result
```

### fetch_swift_data()
```python
def fetch_swift_data(self, bic_code=None):
    """Получение данных по SWIFT коду через API
    
    Args:
        bic_code (str, optional): BIC код для поиска
    
    Returns:
        dict: Словарь с данными банка или None
    """
    # Логика получения данных
```

### search_or_create_swift()
```python
@api.model
def search_or_create_swift(self, bic_code):
    """Поиск или создание SWIFT записи
    
    Args:
        bic_code (str): BIC код для поиска
    
    Returns:
        recordset: Запись amanat.swift
    """
    # Поиск существующей записи
    swift_record = self.search([('bic_code', '=', bic_code)], limit=1)
    
    if not swift_record:
        # Создание новой записи
        swift_record = self.create({'bic_code': bic_code})
    
    return swift_record
```

### search_by_identifier()
```python
@api.model
def search_by_identifier(self, identifier):
    """Поиск SWIFT записи по BIC или UETR
    
    Args:
        identifier (str): BIC код или UETR номер
    
    Returns:
        dict: Информация о банке или None
    """
    # Логика поиска
```

### action_refresh_data()
```python
def action_refresh_data(self):
    """Обновление данных из API"""
    for record in self:
        record.fetch_swift_data()
```

---

## 🔌 API интеграции

### SwiftCodesAPI.com

#### Основной метод
```python
def _fetch_from_swiftbic_com(self, bic_code):
    """Получение данных с SwiftCodesAPI.com
    
    Args:
        bic_code (str): BIC код для поиска
    
    Returns:
        dict: Нормализованные данные или None
    """
    try:
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
                return self._normalize_swift_data(data['data'])
        
        return None
        
    except Exception as e:
        _logger.error(f"Ошибка API: {str(e)}")
        return None
```

#### Нормализация данных
```python
def _normalize_swift_data(self, swift_data):
    """Нормализация данных SwiftCodesAPI.com
    
    Args:
        swift_data (dict): Сырые данные от API
    
    Returns:
        dict: Нормализованные данные
    """
    return {
        'bic_code': self.bic_code.upper(),
        'bank_name': swift_data.get('bank', {}).get('name', ''),
        'bank_name_short': swift_data.get('branch_name', ''),
        'country_code': swift_data.get('country', {}).get('id', ''),
        'country_name': swift_data.get('country', {}).get('name', ''),
        'city': swift_data.get('city', {}).get('name', ''),
        'address': swift_data.get('address', ''),
        'branch_code': swift_data.get('branch_code', ''),
        'swift_network': True,
        'swift_status': 'active',
        'api_response': json.dumps(swift_data, ensure_ascii=False),
        'last_updated': fields.Datetime.now()
    }
```

### UETR API (В разработке)

#### Структура методов
```python
def _fetch_by_uetr(self, uetr_no):
    """Поиск данных по UETR No
    
    Args:
        uetr_no (str): UETR номер
    
    Returns:
        dict: Данные банка или None
    """
    try:
        # Попытка получения данных через реальные API
        real_data = self._fetch_uetr_from_real_apis(uetr_no)
        return real_data
        
    except Exception as e:
        _logger.error(f"Ошибка при получении данных по UETR {uetr_no}: {str(e)}")
        return None

def _fetch_uetr_from_real_apis(self, uetr_no):
    """Получение данных UETR из реальных API
    
    Args:
        uetr_no (str): UETR номер
    
    Returns:
        dict: Данные транзакции или None
    """
    # TODO: Реализовать интеграцию с UETR API
    # Возможные варианты:
    # - SWIFT gpi API
    # - Банковские API
    # - Платные сервисы отслеживания
    
    return None
```

---

## ✅ Валидация данных

### Валидация BIC кода
```python
@api.constrains('bic_code')
def _check_bic_code(self):
    """Проверка корректности BIC кода"""
    for record in self:
        if record.bic_code:
            # Проверка длины
            if len(record.bic_code) not in [8, 11]:
                raise ValidationError(
                    _('BIC код должен содержать 8 или 11 символов. '
                      'Вы ввели: %s (длина: %d)') % (record.bic_code, len(record.bic_code))
                )
            
            # Проверка символов
            if not record.bic_code.isalnum():
                raise ValidationError(
                    _('BIC код может содержать только буквы и цифры')
                )
            
            # Проверка формата
            if not record.bic_code[:4].isalpha():
                raise ValidationError(
                    _('Первые 4 символа BIC кода должны быть буквами')
                )
            
            if not record.bic_code[4:6].isalpha():
                raise ValidationError(
                    _('Символы 5-6 BIC кода должны быть буквами (код страны)')
                )
```

### Валидация UETR
```python
def _validate_uetr_format(self, uetr_no):
    """Валидация формата UETR номера
    
    Args:
        uetr_no (str): UETR номер для проверки
    
    Returns:
        bool: True если формат корректен
    """
    # UETR формат: 8 символов + дефис + 4 символа + дефис + 4 символа + дефис + 4 символа + дефис + 12 символов
    # Например: 44996efa-0a58-4f3f-a315-30bf17b5d147
    
    import re
    uetr_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
    
    return bool(re.match(uetr_pattern, uetr_no.lower()))
```

---

## ❌ Обработка ошибок

### Коды ошибок API
```python
API_ERROR_CODES = {
    200: 'Успешно',
    400: 'Неверный формат запроса',
    401: 'Ошибка аутентификации',
    403: 'Доступ запрещен',
    404: 'Данные не найдены',
    429: 'Превышен лимит запросов',
    500: 'Внутренняя ошибка сервера',
    502: 'Сервер недоступен',
    503: 'Сервис временно недоступен'
}
```

### Обработка ошибок
```python
def _handle_api_error(self, response, bic_code):
    """Обработка ошибок API
    
    Args:
        response: HTTP ответ
        bic_code (str): BIC код для логирования
    
    Returns:
        None
    """
    error_message = self.API_ERROR_CODES.get(response.status_code, 'Неизвестная ошибка')
    
    if response.status_code == 404:
        _logger.warning(f"BIC код {bic_code} не найден в API")
    elif response.status_code == 401:
        _logger.error(f"Ошибка аутентификации API для {bic_code}")
    elif response.status_code == 429:
        _logger.warning(f"Превышен лимит запросов API для {bic_code}")
    else:
        _logger.error(f"API ошибка {response.status_code}: {error_message} для {bic_code}")
```

---

## 💡 Примеры кода

### Создание записи
```python
# Создание новой SWIFT записи
swift_record = self.env['amanat.swift'].create({
    'bic_code': 'DEUTDEFF',
})

# Данные будут автоматически загружены из API
print(swift_record.bank_name)  # "DEUTSCHE BANK AG"
```

### Поиск записи
```python
# Поиск по BIC коду
swift_record = self.env['amanat.swift'].search([
    ('bic_code', '=', 'DEUTDEFF')
], limit=1)

# Поиск или создание
swift_record = self.env['amanat.swift'].search_or_create_swift('DEUTDEFF')
```

### Обновление данных
```python
# Обновление одной записи
swift_record = self.env['amanat.swift'].browse(1)
swift_record.action_refresh_data()

# Массовое обновление
swift_records = self.env['amanat.swift'].search([
    ('last_updated', '<', fields.Datetime.now() - timedelta(days=30))
])
for record in swift_records:
    record.action_refresh_data()
```

### Использование в других моделях
```python
class AmanatZayavka(models.Model):
    _name = 'amanat.zayavka'
    
    swift_id = fields.Many2one('amanat.swift', string='SWIFT Code')
    bic_code = fields.Char(string='BIC Code')
    
    @api.onchange('bic_code')
    def _onchange_bic_code(self):
        if self.bic_code:
            # Автоматическое создание SWIFT записи
            swift_record = self.env['amanat.swift'].search_or_create_swift(self.bic_code)
            self.swift_id = swift_record.id
```

### Работа с чат-ботом
```python
# В модели discuss.channel
def _handle_swift_command(self, command_parts):
    """Обработка команды /swift"""
    if len(command_parts) < 2:
        return "Использование: /swift {BIC_код или UETR}"
    
    identifier = command_parts[1]
    
    # Поиск по идентификатору
    swift_info = self.env['amanat.swift'].search_by_identifier(identifier)
    
    if swift_info:
        # Форматирование ответа
        message = f"""
🏦 **{swift_info.get('bank_name', 'Неизвестно')}**
🏛️ BIC: {swift_info.get('bic_code', 'Неизвестно')}
🌍 Страна: {swift_info.get('country_name', 'Неизвестно')}
🏙️ Город: {swift_info.get('city', 'Неизвестно')}
📍 Адрес: {swift_info.get('address', 'Неизвестно')}
"""
        return message
    else:
        return "⚠️ Информация не найдена в API"
```

---

## 🔧 Настройка и конфигурация

### Настройка API ключей
```python
# В файле config/settings.py или как системная переменная
SWIFT_API_CONFIG = {
    'swiftcodesapi': {
        'api_key': 'sk_1ee274c404a207f4f1e0b47d2638b2cb4cfa688ea757bfe386ecd071281a0647',
        'base_url': 'https://swiftcodesapi.com/v1/swifts/',
        'timeout': 15,
        'retry_count': 3
    }
}
```

### Настройка логирования
```python
# В odoo.conf
[logger_amanat_swift]
level = INFO
handlers = hand01
qualname = addons.amanat.models.swift
propagate = 1
```

### Настройка кэширования
```python
from odoo.tools import cache

class AmanatSwift(models.Model):
    
    @cache('bic_code')
    def _get_cached_swift_data(self, bic_code):
        """Кэширование данных SWIFT"""
        return self._fetch_from_swiftbic_com(bic_code)
```

---

*API Reference последний раз обновлен: 2025-01-07*
*Версия: 1.0.0* 