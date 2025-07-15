# Обзор файлов функционала Preview Offline

## Backend файлы (Python)

### 1. `addons/amanat/models/ir_attachment.py`
- **Назначение**: Расширение модели `ir.attachment` для декодирования содержимого файлов
- **Ключевой метод**: `decode_content(attach_id, doc_type)`
- **Размер**: 262 строки
- **Зависимости**: `pandas`, `python-docx`, `openpyxl`, `xlrd`

### 2. `addons/amanat/models/sverka_files.py`
- **Назначение**: Модель для работы с файлами сверки
- **Ключевой метод**: `preview_files()`
- **Размер**: 55 строк
- **Поля**: `file_attachments`, `attachment_ids`

### 3. `addons/amanat/models/__init__.py`
- **Назначение**: Подключение модели расширения
- **Изменения**: Добавлена строка `from . import ir_attachment`

## Frontend файлы (JavaScript)

### 1. `addons/amanat/static/src/js/attachment_preview.js`
- **Назначение**: Основная логика обработки предпросмотра
- **Размер**: 85 строк
- **Ключевая функция**: `handlePreviewOffline(ev)`
- **Обработка**: Клики по кнопкам предпросмотра, вызов backend методов

### 2. `addons/amanat/static/src/js/attachment_preview_modal.js`
- **Назначение**: Инициализация модального окна
- **Размер**: 46 строк
- **Ключевая функция**: `initAttachmentPreviewModal()`
- **Обработка**: Создание DOM элементов, обработчики событий

### 3. `addons/amanat/static/src/js/attachment_widget_extension.js`
- **Назначение**: Расширение виджетов вложений
- **Размер**: 246 строк
- **Функции**: `onClickPreviewOffline()`, `stopPreviewButton()`
- **Обработка**: Дублирование функциональности для разных контекстов

## Стили (CSS)

### 1. `addons/amanat/static/src/css/attachment_preview.css`
- **Назначение**: Стили для модального окна предпросмотра
- **Размер**: 115 строк
- **Основные элементы**:
  - `#xlsx_preview` - модальное окно
  - `#MyPreview_content` - контейнер содержимого
  - `#MyTable` - стили для Excel таблиц
  - `.MyDocs` - стили для Word документов

## XML шаблоны

### 1. `addons/amanat/static/src/xml/attachment_preview.xml`
- **Назначение**: HTML шаблон модального окна
- **Размер**: 14 строк
- **Элементы**: Структура модального окна, кнопка закрытия

## Представления (Views)

### 1. `addons/amanat/views/sverka_files_views.xml`
- **Назначение**: Представления для модели sverka_files
- **Размер**: 62 строки
- **Особенности**:
  - Виджет `many2many_binary` для вложений
  - Кнопка "Превью файлов" в списке и форме

## Конфигурация

### 1. `addons/amanat/__manifest__.py`
- **Назначение**: Конфигурация модуля
- **Изменения**:
  - Добавлены assets для CSS, JS, XML
  - Добавлены Python зависимости в `external_dependencies`
  - Размер: 172 строки

## Структура файлов

```
addons/amanat/
├── models/
│   ├── ir_attachment.py          # Декодирование файлов
│   ├── sverka_files.py           # Модель сверки
│   └── __init__.py               # Импорт расширения
├── static/src/
│   ├── css/
│   │   └── attachment_preview.css # Стили модального окна
│   ├── js/
│   │   ├── attachment_preview.js        # Основная логика
│   │   ├── attachment_preview_modal.js  # Модальное окно
│   │   └── attachment_widget_extension.js # Расширения виджетов
│   └── xml/
│       └── attachment_preview.xml # HTML шаблон
├── views/
│   └── sverka_files_views.xml    # Представления
├── docs/
│   ├── ATTACHMENT_PREVIEW_DOCUMENTATION.md  # Полная документация
│   └── ATTACHMENT_PREVIEW_FILES_OVERVIEW.md # Этот файл
└── __manifest__.py               # Конфигурация модуля
```

## Зависимости

### Python пакеты
- `pandas` - обработка Excel файлов
- `python-docx` - обработка Word документов
- `openpyxl` - чтение .xlsx файлов
- `xlrd` - чтение .xls файлов

### Odoo модули
- `base` - базовая функциональность
- `mail` - система сообщений
- `web` - веб интерфейс
- `chatter_attachments_manager` - расширенная работа с вложениями

## Размеры файлов

| Файл | Строки | Размер |
|------|--------|---------|
| `ir_attachment.py` | 262 | ~12KB |
| `attachment_preview.js` | 85 | ~3KB |
| `attachment_widget_extension.js` | 246 | ~10KB |
| `attachment_preview.css` | 115 | ~3KB |
| `attachment_preview_modal.js` | 46 | ~2KB |
| `sverka_files.py` | 55 | ~2KB |
| **Общий размер** | **809** | **~32KB** |

## Ключевые особенности

### Модульность
- Каждый файл отвечает за свою область функциональности
- Четкое разделение backend и frontend логики
- Возможность независимой разработки компонентов

### Расширяемость
- Легко добавить новые типы файлов
- Простое расширение UI компонентов
- Гибкая система обработки ошибок

### Совместимость
- Работает с существующими виджетами Odoo
- Интеграция с chatter_attachments_manager
- Поддержка множественных форматов файлов

## Последовательность загрузки

1. **Python**: Загрузка моделей и методов
2. **CSS**: Загрузка стилей для модального окна
3. **JavaScript**: Инициализация обработчиков событий
4. **XML**: Подготовка HTML шаблонов
5. **Views**: Отображение пользовательского интерфейса

## Порядок выполнения

1. Пользователь кликает по кнопке предпросмотра
2. JavaScript получает данные файла
3. Вызывается backend метод `decode_content`
4. Python обрабатывает файл и возвращает HTML/данные
5. JavaScript отображает результат в модальном окне
6. Пользователь может закрыть окно или продолжить работу 