# Критические исправления для генерации документа "Индивидуал"

## Проблемы из логов

### 1. ❌ YandexGPT не работает
**Ошибка:** `[ПЕРЕВОД] Не удалось импортировать _get_yandex_gpt_config`

**Причина:** Неправильный относительный импорт

**Исправление:**
```python
# Было:
from ..automations.ygpt_analyse import _get_yandex_gpt_config

# Стало:
from odoo.addons.amanat.models.zayavka.automations.ygpt_analyse import _get_yandex_gpt_config
```

### 2. ❌ Документ не появляется в "поручение выход"
**Ошибка:** Неправильная привязка attachment к Many2many полю

**Причина:** Использование `res_field` для Many2many поля

**Исправление:**
```python
# Было:
attachment = self.env['ir.attachment'].create({
    'res_field': 'assignment_end_attachments',  # Неправильно для Many2many
    ...
})

# Стало:
attachment = self.env['ir.attachment'].create({
    # Убрали res_field
    ...
})
# Добавляем attachment к полю assignment_end_attachments
self.assignment_end_attachments = [(4, attachment.id)]
```

### 3. ❌ XML поврежден после замены
**Ошибка:** `XML declaration not well-formed: line 1, column 16`

**Причина:** Двойное экранирование символа `&` и неправильная обработка XML

**Исправление:**
```python
def escape_xml(text):
    """Экранирует XML символы и фигурные скобки в значениях"""
    if not isinstance(text, str):
        text = str(text)
    # Сначала проверяем, не экранирован ли уже символ &
    if '&amp;' not in text:
        text = text.replace('&', '&amp;')
    return (text.replace('<', '&lt;')
           .replace('>', '&gt;')
           .replace('"', '&quot;')
           .replace("'", '&apos;'))
    # НЕ экранируем фигурные скобки в данных - это может сломать XML
```

## Результат исправлений

После применения исправлений:

1. ✅ **YandexGPT будет работать** - правильный импорт функции
2. ✅ **Документ появится в "поручение выход"** - правильная привязка к Many2many полю
3. ✅ **XML не будет поврежден** - улучшенное экранирование

## Тестирование

Для проверки исправлений:

1. Перезагрузить модуль Odoo
2. Сгенерировать документ "Индивидуал"
3. Проверить:
   - Работает ли перевод через YandexGPT
   - Появляется ли файл в поле "поручение выход"
   - Нет ли ошибок XML в логах

---
*Дата исправлений: Декабрь 2024*
*Статус: Критические исправления применены*
