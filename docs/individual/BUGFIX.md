# Исправление ошибки загрузки модуля

## Проблема

При загрузке модуля возникала ошибка:

```
ValueError: Wrong value for template.library.category: 'individual'
```

## Причина

В модели `template.library` поле `category` имеет ограниченный набор допустимых значений:

```python
category = fields.Selection([
    ('contract', 'Договоры'),
    ('invoice', 'Счета'),
    ('report', 'Отчеты'),
    ('letter', 'Письма'),
    ('certificate', 'Справки'),
    ('statement', 'Заявления'),
    ('other', 'Прочее')
], string='Категория', default='other')
```

Значение `'individual'` не входит в этот список.

## Решение

Изменили категорию шаблона с `'individual'` на `'other'` в файле `data/demo_template_library.xml`:

**Было:**
```xml
<field name="category">individual</field>
```

**Стало:**
```xml
<field name="category">other</field>
```

## Файлы изменены

1. `/addons/amanat/data/demo_template_library.xml` - исправлена категория шаблона
2. `/addons/amanat/docs/individual/IMPLEMENTATION.md` - обновлена документация

## Альтернативные решения

Если в будущем потребуется отдельная категория для индивидуальных поручений, можно:

1. **Добавить новую категорию в модель:**
```python
# В models/template_library.py
category = fields.Selection([
    ('contract', 'Договоры'),
    ('invoice', 'Счета'),
    ('report', 'Отчеты'),
    ('letter', 'Письма'),
    ('certificate', 'Справки'),
    ('statement', 'Заявления'),
    ('individual', 'Индивидуальные поручения'),  # Новая категория
    ('other', 'Прочее')
], string='Категория', default='other')
```

2. **Обновить XML файл:**
```xml
<field name="category">individual</field>
```

## Статус

✅ **Исправлено** - модуль теперь загружается без ошибок.

---
*Дата исправления: Декабрь 2024*
*Версия: 1.0.1*
