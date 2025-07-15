# Документация по функционалу Preview Offline документов в модуле Amanat

## Обзор

Функционал "Preview Offline" позволяет пользователям просматривать содержимое документов Excel (.xlsx, .xls) и Word (.docx) прямо в интерфейсе Odoo без необходимости скачивания файлов. Функциональность интегрирована в модуль `amanat` и особенно полезна для работы с файлами сверки (`sverka_files`).

## Поддерживаемые форматы файлов

- **Excel файлы**: `.xlsx`, `.xls`
- **Word документы**: `.docx`
- **Ограничения**: Для превью отображается максимум 100 строк и 20 колонок для Excel файлов

## Архитектура системы

### 1. Backend (Python)

#### Модель расширения: `ir_attachment.py`
**Путь**: `addons/amanat/models/ir_attachment.py`

```python
class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    
    @api.model
    def decode_content(self, attach_id, doc_type):
        """Декодирование содержимого файлов XLSX, XLS, DOCX"""
```

**Ключевые особенности**:
- Множественные методы чтения Excel файлов для максимальной совместимости
- Обработка ошибок с детальными сообщениями
- Поддержка файлов как из binary данных, так и с внешних URL
- Ограничения на размер превью для производительности

**Движки для Excel файлов**:
1. `openpyxl` - основной движок для .xlsx
2. `pandas` с различными engine'ами
3. `calamine` - быстрый движок
4. `xlrd` - для старых .xls файлов

### 2. Frontend (JavaScript)

#### Основные JavaScript файлы:

##### 1. `attachment_preview.js`
**Путь**: `addons/amanat/static/src/js/attachment_preview.js`

```javascript
async function handlePreviewOffline(ev) {
    // Основная функция обработки предпросмотра
    const data = await odoo.env.services.orm.call(
        "ir.attachment", 
        "decode_content", 
        [parseInt(attachmentId), fileType]
    );
}
```

**Назначение**: Обработка кликов по кнопкам предпросмотра и отображение данных

##### 2. `attachment_preview_modal.js`
**Путь**: `addons/amanat/static/src/js/attachment_preview_modal.js`

```javascript
function initAttachmentPreviewModal() {
    // Инициализация модального окна
}
```

**Назначение**: Создание и настройка модального окна для предпросмотра

##### 3. `attachment_widget_extension.js`
**Путь**: `addons/amanat/static/src/js/attachment_widget_extension.js`

**Назначение**: Расширение функциональности виджетов вложений

### 3. Стили (CSS)

#### Файл стилей: `attachment_preview.css`
**Путь**: `addons/amanat/static/src/css/attachment_preview.css`

**Основные стили**:
- Модальное окно `#xlsx_preview`
- Контейнер содержимого `#MyPreview_content`
- Стили для Excel таблиц `#MyTable`, `.dataframe`
- Стили для Word документов `.MyDocs`

### 4. XML шаблоны

#### Шаблон модального окна: `attachment_preview.xml`
**Путь**: `addons/amanat/static/src/xml/attachment_preview.xml`

```xml
<div id="xlsx_preview" class="modal">
    <div class="modal-content" id="MyPreview_content">
        <span class="close" id="stop-preview-button">×</span>
        <h1 id="FileHead"></h1>
        <div class="XlsxTable"></div>
        <div class="MyDocs"></div>
    </div>
</div>
```

## Интеграция с модулем Sverka Files

### Модель данных
**Путь**: `addons/amanat/models/sverka_files.py`

```python
class AmanatSverkaFiles(models.Model, AmanatBaseModel):
    _name = 'amanat.sverka_files'
    
    file_attachments = fields.Many2many('ir.attachment', string='Документы')
    
    def preview_files(self):
        """Метод для превью файлов с вызовом модального окна"""
```

### Представления
**Путь**: `addons/amanat/views/sverka_files_views.xml`

```xml
<field name="file_attachments" widget="many2many_binary" 
       options="{'no_create': False, 'no_open': False}"/>
```

## Установка и настройка

### 1. Python зависимости

**Добавлено в `__manifest__.py`**:
```python
"external_dependencies": {
    "python": ["pandas", "python-docx", "openpyxl", "xlrd"]
}
```

**Команда установки**:
```bash
pip3 install pandas python-docx openpyxl xlrd
```

### 2. Подключение ресурсов

**В `__manifest__.py`**:
```python
"assets": {
    "web.assets_backend": [
        "amanat/static/src/css/attachment_preview.css",
        "amanat/static/src/js/attachment_preview.js",
        "amanat/static/src/js/attachment_preview_modal.js",
        "amanat/static/src/js/attachment_widget_extension.js",
        "amanat/static/src/xml/attachment_preview.xml",
    ],
},
```

### 3. Зависимости модуля

```python
"depends": [
    "base", "mail", "web", "chatter_attachments_manager"
],
```

## Использование

### 1. Автоматическая интеграция

Функциональность автоматически доступна везде, где используются вложения:
- В чаттере любых записей
- В полях many2many_binary
- В стандартных виджетах вложений

### 2. Кнопка предпросмотра

При наведении на файл Excel или Word появляется кнопка "Preview Offline":
- Для Excel: отображается таблица с данными
- Для Word: отображается текст параграфами

### 3. Модальное окно

Предпросмотр открывается в модальном окне с возможностью:
- Прокрутки содержимого
- Закрытия по кнопке X
- Закрытия по клику на фон

## Принцип работы

### 1. Клик по кнопке предпросмотра
```javascript
// Получение данных файла
const attachmentId = target.dataset.attachmentId;
const fileType = target.dataset.fileType;
const fileName = target.dataset.fileName;
```

### 2. Вызов backend метода
```javascript
const data = await odoo.env.services.orm.call(
    "ir.attachment", 
    "decode_content", 
    [parseInt(attachmentId), fileType]
);
```

### 3. Обработка на backend
```python
def decode_content(self, attach_id, doc_type):
    # Получение файла
    attachment = self.sudo().browse(attach_id)
    xlsx_data = base64.b64decode(attachment.datas)
    
    # Обработка в зависимости от типа
    if doc_type == 'xlsx':
        content = pd.read_excel(BytesIO(xlsx_data), engine='openpyxl')
        return content.to_html(index=False)
    elif doc_type == 'docx':
        doc = DocxDocument(io.BytesIO(xlsx_data))
        return [p.text for p in doc.paragraphs]
```

### 4. Отображение результата
```javascript
// Для Excel
xlsxTable.innerHTML = data;

// Для Word
data.forEach(para => {
    const p = document.createElement('p');
    p.textContent = para;
    myDocs.appendChild(p);
});
```

## Обработка ошибок

### Python уровень
- Проверка существования файла
- Множественные методы чтения Excel
- Детальные сообщения об ошибках с рекомендациями

### JavaScript уровень
- Проверка наличия необходимых элементов DOM
- Обработка ошибок сети
- Отображение пользовательских сообщений об ошибках

## Производительность

### Ограничения
- Максимум 100 строк для Excel файлов
- Максимум 20 колонок для Excel файлов
- Таймаут 30 секунд для загрузки файлов с URL

### Оптимизации
- Использование `read_only=True` для Excel файлов
- Ограничение `nrows=500` при чтении
- Кэширование модального окна в DOM

## Совместимость

### Поддерживаемые версии Excel
- Excel 2007+ (.xlsx)
- Excel 97-2003 (.xls)

### Поддерживаемые версии Word
- Word 2007+ (.docx)

### Браузеры
- Chrome 70+
- Firefox 60+
- Safari 12+
- Edge 79+

## Устранение проблем

### Частые ошибки

1. **"Файл не найден"**
   - Проверьте наличие файла в системе
   - Убедитесь в правильности ID вложения

2. **"Не удалось прочитать xlsx файл"**
   - Пересохраните файл в Excel без макросов
   - Проверьте, что файл не защищен паролем
   - Экспортируйте в CSV для проверки

3. **"Modal elements not found"**
   - Перезагрузите страницу
   - Проверьте загрузку JS файлов

### Логи и отладка

```python
# Включение логов в Python
import logging
_logger = logging.getLogger(__name__)
_logger.info("Preview file processing: %s", attachment.name)
```

```javascript
// Отладка в JavaScript
console.log('Attachment ID:', attachmentId);
console.log('File type:', fileType);
```

## Расширение функциональности

### Добавление новых типов файлов

1. Расширьте метод `decode_content` в `ir_attachment.py`
2. Добавьте обработку в JavaScript файлы
3. Обновите CSS стили при необходимости

### Интеграция с другими модулями

```python
# В вашем модуле
def your_preview_method(self):
    return {
        'type': 'ir.actions.client',
        'tag': 'call_js_function',
        'params': {
            'function_name': 'handlePreviewOffline',
            'args': [attachment_id, file_type],
        }
    }
```

## Заключение

Функционал Preview Offline обеспечивает удобный способ просмотра документов без необходимости их скачивания. Он хорошо интегрируется с существующей системой вложений Odoo и предоставляет расширенные возможности для работы с файлами в модуле Amanat.

Для поддержки и вопросов обращайтесь к документации Odoo и исходному коду модуля `chatter_attachments_manager`, на котором основана эта функциональность. 