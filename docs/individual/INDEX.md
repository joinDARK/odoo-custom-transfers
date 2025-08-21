# Документация модуля "Индивидуал" - Оглавление

## 📋 Обзор документации

Полная документация по модулю генерации документа "Индивидуал" для системы Amanat в Odoo 18.

## 📚 Структура документации

### 🏠 [README.md](README.md)
**Основная документация модуля**
- Описание функциональности
- Быстрый старт
- Требования к системе
- Поддерживаемые поля
- Обзор возможностей

### 🔧 [IMPLEMENTATION.md](IMPLEMENTATION.md)
**Техническая документация для разработчиков**
- Архитектура решения
- Подробное описание методов
- Алгоритмы работы
- Интеграция с существующей системой
- Конфигурация и настройка

### 🗂️ [FIELD_MAPPING.md](FIELD_MAPPING.md)
**Сопоставление полей документа**
- Полная таблица сопоставления полей
- Детальное описание обработки каждого поля
- Примеры форматирования
- Обработка пустых значений
- Валидация данных

### 🤖 [YANDEX_GPT_INTEGRATION.md](YANDEX_GPT_INTEGRATION.md)
**Интеграция с YandexGPT для переводов**
- Настройка YandexGPT API
- Реализация переводов
- Примеры переводов
- Обработка ошибок
- Безопасность и мониторинг

### 👤 [USER_GUIDE.md](USER_GUIDE.md)
**Руководство пользователя**
- Пошаговые инструкции
- Работа с интерфейсом
- Устранение неполадок
- Советы по эффективному использованию
- Часто задаваемые вопросы

## 🚀 Быстрая навигация

### Для пользователей
1. **Начать работу:** [USER_GUIDE.md](USER_GUIDE.md) → "Пошаговая инструкция"
2. **Проблемы:** [USER_GUIDE.md](USER_GUIDE.md) → "Устранение неполадок"
3. **Вопросы:** [USER_GUIDE.md](USER_GUIDE.md) → "Часто задаваемые вопросы"

### Для администраторов
1. **Установка:** [README.md](README.md) → "Установка и настройка"
2. **Настройка YandexGPT:** [YANDEX_GPT_INTEGRATION.md](YANDEX_GPT_INTEGRATION.md) → "Настройка YandexGPT"
3. **Поля документа:** [FIELD_MAPPING.md](FIELD_MAPPING.md) → "Полная таблица сопоставления"

### Для разработчиков
1. **Архитектура:** [IMPLEMENTATION.md](IMPLEMENTATION.md) → "Архитектура решения"
2. **API методы:** [IMPLEMENTATION.md](IMPLEMENTATION.md) → "Подробное описание методов"
3. **Интеграция:** [IMPLEMENTATION.md](IMPLEMENTATION.md) → "Интеграция с существующей системой"

## 📊 Сводная информация

### Основные файлы модуля
```
models/zayavka/methods.py          # Основная логика генерации
views/zayavka_views.xml           # Интерфейс пользователя
data/demo_template_library.xml    # Конфигурация шаблона
static/src/template_documents/    # Шаблоны документов
```

### Ключевые методы
- `action_generate_individual_document()` - Генерация документа
- `_prepare_individual_template_data()` - Подготовка данных
- `_translate_text_via_yandex_gpt()` - Перевод через YandexGPT
- `_convert_docx_to_pdf_base64()` - Конвертация в PDF

### Поддерживаемые форматы
- **DOCX** - Microsoft Word документ
- **PDF** - Portable Document Format (через конвертацию)

### Языки
- **Русский** - Исходные данные и интерфейс
- **Английский** - Автоматический перевод через YandexGPT

## 🔗 Связанная документация

### Модули Amanat
- [YandexGPT Integration](../README_YANDEX_GPT_INTEGRATION.md)
- [Template Library](../models/template_library.md)
- [Document Generation](../README_document_analysis.md)

### Внешние зависимости
- [YandexGPT API Documentation](https://cloud.yandex.ru/docs/yandexgpt/)
- [LibreOffice Headless Mode](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)
- [Odoo 18 Documentation](https://www.odoo.com/documentation/18.0/)

## 📝 Версионирование документации

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0.0 | 2024-12-XX | Первоначальная версия документации |

## 🤝 Вклад в документацию

Для улучшения документации:
1. Создайте issue с описанием проблемы
2. Предложите изменения через pull request
3. Обратитесь к команде разработки

## 📞 Контакты

**Техническая поддержка:**
- Email: support@amanat.com
- Telegram: @amanat_support

**Разработка:**
- GitHub: github.com/amanat/odoo-modules
- Email: dev@amanat.com

---

*Документация обновлена: Декабрь 2024*
*Версия модуля: 1.0.0*
*Совместимость: Odoo 18.0+*
