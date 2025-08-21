# Сопоставление полей документа "Индивидуал"

## Полная таблица сопоставления

| № | Сигнатура в шаблоне | Поле модели | Тип обработки | Пример значения |
|---|---------------------|-------------|---------------|-----------------|
| 1 | `{{номер_п}}` | `instruction_number` | Прямая подстановка | `Т-12345` |
| 2 | `{{подписан_а_с}}` | `agent_contract_date` | Русский формат даты | `«15» Декабря 2024` |
| 3 | `{{подписано_п}}` | `instruction_signed_date` | Русский формат даты | `«18» Августа 2025` |
| 4 | `{{order_s}}` | `instruction_signed_date` | Английский формат даты | `August 18, 2025` |
| 5 | `{{агент}}` | `agent_id.name` | Прямая подстановка | `ТДК` |
| 6 | `{{agent}}` | `agent_id.name` | Перевод через YandexGPT | `TDK` |
| 7 | `{{клиент}}` | `client_id.name` | Прямая подстановка | `ООО "Импекс-Ф"` |
| 8 | `{{client}}` | `client_id.name` | Перевод через YandexGPT | `Implex-F LLC` |
| 9 | `{{наименование_покупателя_продавца}}` | `exporter_importer_name` | Прямая подстановка | `ZHEJIANG INDUSTRY CO LTD` |
| 10 | `{{адрес_получателя}}` | `beneficiary_address` | Прямая подстановка | `г. Москва, ул. Ленина, д.1` |
| 11 | `{{банк_получателя}}` | `beneficiary_bank_name` | Прямая подстановка | `Сбербанк России` |
| 12 | `{{адрес_банка_получателя}}` | `bank_address` | Прямая подстановка | `г. Москва, ул. Вавилова, д.19` |
| 13 | `{{swift_код}}` | `bank_swift` | Прямая подстановка | `SABRRUMM` |
| 14 | `{{сумма}}` | `amount` | Форматирование (2 знака) | `150000.00` |
| 15 | `{{валюта}}` | `currency` | Верхний регистр | `USD` |
| 16 | `{{курс}}` | `rate_field` | Форматирование (4 знака) | `95.5000` |

## Детальное описание обработки полей

### 1. Номер поручения (`{{номер_п}}`)
**Источник:** `self.instruction_number`
**Обработка:** Прямая подстановка без изменений
```python
instruction_number = self.instruction_number or ""
```

### 2. Дата подписания агент-субагент (`{{подписан_а_с}}`)
**Источник:** `self.agent_contract_date`
**Обработка:** Форматирование в русском стиле
```python
def format_russian_date(date_obj):
    if not date_obj:
        return ""
    day = date_obj.day
    month = russian_months.get(date_obj.month)
    year = date_obj.year
    return f'«{day}» {month} {year}'
```
**Пример:** `2024-12-15` → `«15» Декабря 2024`

### 3. Дата подписания поручения - русский (`{{подписано_п}}`)
**Источник:** `self.instruction_signed_date`
**Обработка:** Форматирование в русском стиле
**Пример:** `2025-08-18` → `«18» Августа 2025`

### 4. Дата подписания поручения - английский (`{{order_s}}`)
**Источник:** `self.instruction_signed_date`
**Обработка:** Форматирование в английском стиле
```python
def format_english_date(date_obj):
    if not date_obj:
        return ""
    day = date_obj.day
    month = english_months.get(date_obj.month)
    year = date_obj.year
    return f'{month} {day}, {year}'
```
**Пример:** `2025-08-18` → `August 18, 2025`

### 5. Агент - русский (`{{агент}}`)
**Источник:** `self.agent_id.name`
**Обработка:** Прямая подстановка
```python
agent_name_ru = str(self.agent_id.name).strip() if self.agent_id and self.agent_id.name else ""
```

### 6. Агент - английский (`{{agent}}`)
**Источник:** `self.agent_id.name`
**Обработка:** Перевод через YandexGPT
```python
agent_name_en = self._translate_text_via_yandex_gpt(agent_name_ru)
```
**Примеры переводов:**
- `ТДК` → `TDK`
- `СТЕЛЛАР` → `STELLAR`
- `Банк Развития` → `Development Bank`

### 7. Клиент - русский (`{{клиент}}`)
**Источник:** `self.client_id.name`
**Обработка:** Прямая подстановка
```python
client_name_ru = str(self.client_id.name).strip() if self.client_id and self.client_id.name else ""
```

### 8. Клиент - английский (`{{client}}`)
**Источник:** `self.client_id.name`
**Обработка:** Перевод через YandexGPT
```python
client_name_en = self._translate_text_via_yandex_gpt(client_name_ru)
```
**Примеры переводов:**
- `ООО "Импекс-Ф"` → `Implex-F LLC`
- `АО "Сбербанк"` → `Sberbank JSC`
- `ИП Иванов И.И.` → `Ivanov I.I. Individual Entrepreneur`

### 9-13. Банковские реквизиты
**Обработка:** Прямая подстановка с проверкой на пустые значения
```python
beneficiary_address = str(self.beneficiary_address).strip() if self.beneficiary_address else ""
beneficiary_bank_name = str(self.beneficiary_bank_name).strip() if self.beneficiary_bank_name else ""
bank_address = str(self.bank_address).strip() if self.bank_address else ""
bank_swift = str(self.bank_swift).strip() if self.bank_swift else ""
```

### 14. Сумма (`{{сумма}}`)
**Источник:** `self.amount`
**Обработка:** Форматирование с 2 знаками после запятой
```python
amount = f"{self.amount:.2f}" if self.amount else "0.00"
```
**Примеры:**
- `150000` → `150000.00`
- `1234.5` → `1234.50`
- `None` → `0.00`

### 15. Валюта (`{{валюта}}`)
**Источник:** `self.currency`
**Обработка:** Приведение к верхнему регистру
```python
currency = str(self.currency).upper() if self.currency else ""
```
**Примеры:**
- `usd` → `USD`
- `eur` → `EUR`
- `rub` → `RUB`

### 16. Курс (`{{курс}}`)
**Источник:** `self.rate_field`
**Обработка:** Форматирование с 4 знаками после запятой
```python
rate = f"{self.rate_field:.4f}" if self.rate_field else ""
```
**Примеры:**
- `95.5` → `95.5000`
- `100.123456` → `100.1235`
- `None` → `""`

## Обработка пустых значений

Все поля имеют защиту от пустых значений:

```python
# Для строковых полей
field_value = str(self.field_name).strip() if self.field_name else ""

# Для числовых полей
numeric_value = f"{self.field_name:.2f}" if self.field_name else "0.00"

# Для дат
date_value = format_date(self.date_field) if self.date_field else ""

# Для связанных полей
related_value = str(self.related_id.name).strip() if self.related_id and self.related_id.name else ""
```

## Логирование значений полей

Система логирует все подготовленные значения для отладки:

```python
_logger.info(f"=== ДАННЫЕ ДЛЯ ШАБЛОНА ИНДИВИДУАЛ ===")
_logger.info(f"Номер поручения: '{instruction_number}'")
_logger.info(f"Дата агент-субагент: '{agent_contract_date_formatted}'")
_logger.info(f"Дата поручения (RU): '{instruction_signed_date_ru}'")
_logger.info(f"Дата поручения (EN): '{instruction_signed_date_en}'")
_logger.info(f"Агент (RU): '{agent_name_ru}'")
_logger.info(f"Агент (EN): '{agent_name_en}'")
_logger.info(f"Клиент (RU): '{client_name_ru}'")
_logger.info(f"Клиент (EN): '{client_name_en}'")
```

## Особенности работы с таблицами

При заполнении таблиц в шаблоне:

1. **Сохранение структуры:** Система не изменяет структуру таблицы, только заменяет содержимое ячеек
2. **Двуязычные таблицы:** Поддерживается одновременное заполнение русских и английских колонок
3. **Форматирование:** Сохраняется исходное форматирование ячеек (шрифт, цвет, границы)

## Валидация данных

Перед генерацией документа выполняется валидация:

```python
# Проверка обязательных полей
if not self.instruction_number:
    _logger.warning("Отсутствует номер поручения")

# Проверка дат
if not self.instruction_signed_date:
    _logger.warning("Отсутствует дата подписания поручения")

# Проверка связанных объектов
if not self.agent_id:
    _logger.warning("Не указан агент")
if not self.client_id:
    _logger.warning("Не указан клиент")
```
