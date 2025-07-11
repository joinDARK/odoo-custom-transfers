# 📚 SWIFT/BIC Модуль - Полная документация

## 📋 Содержание

1. [Обзор системы](#обзор-системы)
2. [Архитектура](#архитектура)
3. [Что уже реализовано](#что-уже-реализовано)
4. [API интеграции](#api-интеграции)
5. [Модель данных](#модель-данных)
6. [Бот команды](#бот-команды)
7. [Что нужно сделать](#что-нужно-сделать)
8. [Инструкции по настройке](#инструкции-по-настройке)
9. [Примеры использования](#примеры-использования)
10. [Устранение неполадок](#устранение-неполадок)

---

## 📊 Обзор системы

SWIFT/BIC модуль предназначен для работы с банковскими кодами и обеспечивает:

- **Автоматическое получение данных** о банках по BIC/SWIFT кодам
- **Проверку и валидацию** банковских кодов
- **Поиск по UETR** (Unique End-to-End Transaction Reference)
- **Интеграцию с чат-ботом** для быстрого поиска информации
- **Связь с заявками** для отслеживания операций

### 🎯 Основные возможности

- ✅ Валидация BIC/SWIFT кодов (8 или 11 символов)
- ✅ Автоматическое получение данных банков через API
- ✅ Поиск по UETR кодам
- ✅ Интеграция с чат-ботом (`/swift команда`)
- ✅ Связь с заявками (`amanat.zayavka`)
- ✅ Отслеживание изменений (mail.thread)
- ✅ Статистика по заявкам

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    SWIFT/BIC Модуль                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │   Бот команды    │    │   Web интерфейс  │              │
│  │   /swift {код}   │    │   Формы, списки  │              │
│  └──────────────────┘    └──────────────────┘              │
│           │                        │                        │
│           └────────────────────────┼────────────────────────┘
│                                    │
│  ┌─────────────────────────────────────────────────────────┐
│  │              Модель amanat.swift                        │
│  │                                                         │
│  │  • Валидация BIC кодов                                  │
│  │  • Автоматическое получение данных                      │
│  │  • Поиск по UETR                                        │
│  │  • Связь с заявками                                     │
│  └─────────────────────────────────────────────────────────┘
│                                    │
│  ┌─────────────────────────────────────────────────────────┐
│  │                 API Интеграции                          │
│  │                                                         │
│  │  • SwiftCodesAPI.com (основной)                         │
│  │  • Fallback механизмы (убраны)                          │
│  │  • UETR API (в разработке)                              │
│  └─────────────────────────────────────────────────────────┘
│                                    │
│  ┌─────────────────────────────────────────────────────────┐
│  │                База данных                              │
│  │                                                         │
│  │  • Записи SWIFT/BIC                                     │
│  │  • Связи с заявками                                     │
│  │  • История изменений                                    │
│  └─────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Что уже реализовано

### 1. **Базовый модуль**
- ✅ Модель `amanat.swift` с полным набором полей
- ✅ Валидация BIC кодов (формат, длина, символы)
- ✅ Автоматическое создание записей при вводе BIC
- ✅ Отслеживание изменений через `mail.thread`

### 2. **API интеграция**
- ✅ **SwiftCodesAPI.com** - основной рабочий API
  - Endpoint: `https://swiftcodesapi.com/v1/swifts/{bic_code}`
  - Аутентификация через `X-Api-Key`
  - Полные данные о банках
- ✅ Обработка различных HTTP статусов (404, 401, 429)
- ✅ Подробное логирование операций

### 3. **Бот интеграция**
- ✅ Команда `/swift {код}` в чате
- ✅ Поиск по BIC и UETR кодам
- ✅ Красивое форматирование ответов
- ✅ Обработка ошибок с информативными сообщениями

### 4. **Модель данных**
- ✅ Основные поля: bic_code, bank_name, country_code, city, address
- ✅ Дополнительные поля: uetr_no, swift_status, swift_network
- ✅ Технические поля: api_response, last_updated
- ✅ Связи: One2many с заявками

### 5. **Пользовательский интерфейс**
- ✅ Форма создания/редактирования SWIFT записей
- ✅ Список записей с фильтрами
- ✅ Кнопка "Обновить данные" для повторного запроса к API
- ✅ Счетчик связанных заявок

---

## 🔌 API интеграции

### SwiftCodesAPI.com (Основной API)

**Конфигурация:**
```python
API_KEY = "sk_1ee274c404a207f4f1e0b47d2638b2cb4cfa688ea757bfe386ecd071281a0647"
BASE_URL = "https://swiftcodesapi.com/v1/swifts/"
```

**Структура ответа:**
```json
{
  "success": true,
  "data": {
    "id": "DEUTDEFF",
    "address": "TAUNUSANLAGE 12",
    "postcode": "60262",
    "branch_name": "Deutsche Bank Frankfurt F",
    "branch_code": "",
    "country": {
      "id": "DE",
      "name": "Germany"
    },
    "city": {
      "id": "uuid",
      "country_id": "DE",
      "name": "Frankfurt Am Main"
    },
    "bank": {
      "id": "uuid",
      "country_id": "DE",
      "code": "DEUT",
      "name": "DEUTSCHE BANK AG"
    }
  }
}
```

**Маппинг данных:**
```python
normalized_data = {
    'bic_code': bic_code.upper(),
    'bank_name': swift_data.get('bank', {}).get('name', ''),
    'bank_name_short': swift_data.get('branch_name', '') or swift_data.get('bank', {}).get('name', ''),
    'country_code': swift_data.get('country', {}).get('id', ''),
    'country_name': swift_data.get('country', {}).get('name', ''),
    'city': swift_data.get('city', {}).get('name', ''),
    'address': swift_data.get('address', ''),
    'branch_code': swift_data.get('branch_code', ''),
    'swift_network': True,
    'swift_status': 'active',
    'api_response': json.dumps(data, ensure_ascii=False),
    'last_updated': fields.Datetime.now()
}
```

### Коды ошибок API:
- `200` - Успешно
- `400` - Неверный формат BIC кода
- `401` - Ошибка аутентификации
- `404` - BIC код не найден
- `429` - Превышен лимит запросов

---

## 🗄️ Модель данных

### Основные поля:

| Поле | Тип | Описание |
|------|-----|----------|
| `bic_code` | Char(11) | BIC/SWIFT код банка |
| `bank_name` | Char | Полное название банка |
| `bank_name_short` | Char | Сокращенное название |
| `country_code` | Char(2) | ISO код страны |
| `country_name` | Char | Название страны |
| `city` | Char | Город банка |
| `address` | Text | Полный адрес |
| `branch_code` | Char(3) | Код филиала |

### Дополнительные поля:

| Поле | Тип | Описание |
|------|-----|----------|
| `uetr_no` | Char | Уникальный номер транзакции |
| `swift_status` | Selection | Статус (active/inactive/suspended/pending/unknown) |
| `swift_network` | Boolean | Подключен к SWIFT сети |
| `is_active` | Boolean | Активен ли код |

### Технические поля:

| Поле | Тип | Описание |
|------|-----|----------|
| `api_response` | Text | Полный ответ от API |
| `last_updated` | Datetime | Время последнего обновления |

### Связи:

| Поле | Тип | Описание |
|------|-----|----------|
| `zayavka_ids` | One2many | Связанные заявки |
| `zayavka_count` | Integer | Количество заявок (вычисляемое) |

---

## 🤖 Бот команды

### Команда `/swift`

**Синтаксис:**
```
/swift {код}
```

**Примеры использования:**
```
/swift DEUTDEFF
/swift 44996efa-0a58-4f3f-a315-30bf17b5d147
/swift BMRIIDJA
```

**Логика работы:**
1. Парсинг входного кода
2. Определение типа (BIC или UETR)
3. Поиск в локальной базе
4. Если не найдено - создание новой записи
5. Запрос к API для получения данных
6. Форматирование и отправка ответа

**Возможные ответы:**
- ✅ Успешно найдено - полная информация о банке
- ⚠️ Не найдено в API - информативное сообщение
- ❌ Ошибка формата - подсказка по исправлению

---

## ⚠️ Что нужно сделать

### 1. **Высокий приоритет**

#### 🔴 UETR API интеграция
- [ ] Найти и подключить рабочий API для UETR кодов
- [ ] Реализовать методы `_fetch_uetr_from_real_apis()`
- [ ] Настроить аутентификацию для платных сервисов
- [ ] Протестировать с реальными UETR кодами

#### 🔴 Обработка ошибок
- [ ] Улучшить обработку сетевых ошибок
- [ ] Добавить retry механизм для временных сбоев
- [ ] Настроить fallback для критических ошибок API

#### 🔴 Пользовательский интерфейс
- [ ] Создать представления для SWIFT записей
- [ ] Добавить меню в главную навигацию
- [ ] Реализовать массовое обновление данных

### 2. **Средний приоритет**

#### 🟡 Производительность
- [ ] Кэширование API ответов
- [ ] Батч-обработка запросов
- [ ] Индексы для быстрого поиска

#### 🟡 Расширенные функции
- [ ] Поиск по части названия банка
- [ ] Фильтрация по странам
- [ ] Экспорт данных в Excel/CSV

#### 🟡 Интеграция с заявками
- [ ] Автоматическое определение SWIFT при создании заявки
- [ ] Валидация банковских реквизитов
- [ ] Отчеты по банкам

### 3. **Низкий приоритет**

#### 🟢 Дополнительные возможности
- [ ] Поддержка IBAN кодов
- [ ] История изменений курсов валют
- [ ] Уведомления об изменениях данных банков

#### 🟢 Документация
- [ ] Создать пользовательское руководство
- [ ] API документация для разработчиков
- [ ] Видео инструкции

---

## ⚙️ Инструкции по настройке

### 1. **Установка модуля**

```bash
# Переход в папку аддонов
cd /home/incube/Documents/odoo/addons/amanat

# Обновление модуля
sudo -u odoo odoo-bin -u amanat -d your_database
```

### 2. **Настройка API ключа**

Обновите API ключ в файле `models/swift.py`:

```python
# В методе _fetch_from_swiftbic_com()
api_key = "ваш_новый_api_ключ_здесь"
```

### 3. **Настройка логирования**

Добавьте в `odoo.conf`:

```ini
[logger_amanat_swift]
level=INFO
handlers=hand01
qualname=addons.amanat.models.swift
```

### 4. **Настройка прав доступа**

Проверьте права в `security/ir.model.access.csv`:

```csv
access_amanat_swift_user,amanat.swift.user,model_amanat_swift,base.group_user,1,1,1,0
access_amanat_swift_manager,amanat.swift.manager,model_amanat_swift,base.group_system,1,1,1,1
```

---

## 💡 Примеры использования

### 1. **Создание SWIFT записи через код**

```python
# Поиск или создание SWIFT записи
swift_record = self.env['amanat.swift'].search_or_create_swift('DEUTDEFF')

# Прямое создание
swift_record = self.env['amanat.swift'].create({
    'bic_code': 'DEUTDEFF',
})
# Данные будут автоматически получены через API
```

### 2. **Поиск по идентификатору**

```python
# Поиск по BIC или UETR
swift_info = self.env['amanat.swift'].search_by_identifier('DEUTDEFF')
swift_info = self.env['amanat.swift'].search_by_identifier('44996efa-0a58-4f3f-a315-30bf17b5d147')
```

### 3. **Обновление данных**

```python
# Обновление одной записи
swift_record.action_refresh_data()

# Обновление всех записей
swift_records = self.env['amanat.swift'].search([])
for record in swift_records:
    record.action_refresh_data()
```

### 4. **Использование в заявках**

```python
# В модели заявки
def create(self, vals):
    # Автоматическое создание SWIFT записи
    if vals.get('bic_code'):
        swift_record = self.env['amanat.swift'].search_or_create_swift(vals['bic_code'])
        vals['swift_id'] = swift_record.id
    
    return super().create(vals)
```

---

## 🚨 Устранение неполадок

### Проблема: "API недоступен"

**Причины:**
- Неверный API ключ
- Превышен лимит запросов
- Сетевые проблемы

**Решение:**
```python
# Проверка API ключа
import requests
response = requests.get(
    'https://swiftcodesapi.com/v1/swifts/DEUTDEFF',
    headers={'X-Api-Key': 'ваш_ключ'}
)
print(response.status_code, response.text)
```

### Проблема: "BIC код не найден"

**Причины:**
- Неверный формат кода
- Код не существует в базе API
- Банк неактивен

**Решение:**
1. Проверьте формат: 8 или 11 символов
2. Убедитесь что код активен
3. Попробуйте альтернативные варианты

### Проблема: "Медленная работа"

**Причины:**
- Много запросов к API
- Отсутствие кэширования
- Большие API ответы

**Решение:**
```python
# Добавить кэширование
@api.model
def _get_cached_swift_data(self, bic_code):
    cache_key = f"swift_{bic_code}"
    cached_data = self.env.cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Получить данные и закэшировать
    data = self._fetch_from_swiftbic_com(bic_code)
    self.env.cache.set(cache_key, data, timeout=3600)
    return data
```

---

## 📊 Статистика и мониторинг

### Важные метрики:

- **Количество SWIFT записей**: `SELECT COUNT(*) FROM amanat_swift`
- **Успешность API запросов**: Анализ логов
- **Время ответа API**: Мониторинг производительности
- **Использование бота**: Статистика команд `/swift`

### Рекомендуемые действия:

1. **Еженедельная проверка** API лимитов
2. **Ежемесячное обновление** данных банков
3. **Квартальный анализ** использования системы
4. **Годовая ревизия** интеграций

---

## 📝 Changelog

### Версия 1.0.0 (Текущая)
- ✅ Базовая модель amanat.swift
- ✅ Интеграция с SwiftCodesAPI.com
- ✅ Бот команды
- ✅ Связь с заявками

### Планируемые версии:

#### Версия 1.1.0
- 🔄 UETR API интеграция
- 🔄 Улучшенный UI
- 🔄 Кэширование

#### Версия 1.2.0
- 🔄 Поддержка IBAN
- 🔄 Отчеты и аналитика
- 🔄 Массовые операции

---

## 👥 Контакты и поддержка

Для вопросов и поддержки:
- 📧 Email: admin@company.com
- 📱 Telegram: @admin_bot
- 🐛 Issues: Внутренняя система багтрекера

---

*Документация последний раз обновлена: 2025-01-07*
*Версия модуля: 1.0.0* 