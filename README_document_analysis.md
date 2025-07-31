# Анализ текста документов

## Описание

Добавлена функциональность для анализа текста документов из полей `zayavka_attachments` и `screen_sber_attachments`. Функция извлекает весь текст из PDF и DOCX файлов, исключая белые сигнатуры "Подпись" и "Печать".

## Функции

### `analyze_document_text()`
Основная функция для анализа документов. Обрабатывает все файлы из указанных полей и возвращает структурированные данные.

### `action_analyze_document_text()`
Action-метод для вызова из интерфейса Odoo. Показывает уведомления о результатах анализа.

### `_extract_text_from_attachment(attachment, field_type)`
Извлекает текст из конкретного вложения.

### `_extract_text_from_pdf(pdf_data)`
Извлекает текст из PDF, исключая белые сигнатуры.

### `_format_analysis_json(analysis_data)`
Форматирует результаты в JSON и выводит в консоль.

## Использование

### Из кода Python:
```python
# Получаем заявку
zayavka = self.env['amanat.zayavka'].browse(zayavka_id)

# Анализируем документы
results = zayavka.analyze_document_text()
```

### Из интерфейса:
Можно добавить кнопку в представление заявки:
```xml
<button name="action_analyze_document_text" 
        string="Анализировать текст документов" 
        type="object" 
        class="btn-primary"/>
```

## Формат результата JSON

```json
{
  "zayavka_id": 123,
  "zayavka_num": "ZAY-001",
  "analysis_timestamp": "2024-01-15T10:30:00",
  "total_files_analyzed": 2,
  "files": [
    {
      "attachment_id": 456,
      "attachment_name": "zayvka.pdf",
      "field_type": "zayavka",
      "file_type": "pdf",
      "extracted_text": [
        {
          "page": 1,
          "text": "Текст первой страницы..."
        },
        {
          "page": 2,
          "text": "Текст второй страницы..."
        }
      ],
      "text_length": 2,
      "creation_date": "2024-01-15T09:00:00"
    }
  ]
}
```

## Требования

- PyMuPDF (устанавливается через pip install pymupdf)
- LibreOffice (для конвертации DOCX в PDF)

## Особенности

1. **Поддерживаемые форматы**: PDF и DOCX
2. **Исключение сигнатур**: Автоматически исключается белый текст "Подпись" и "Печать"
3. **Обработка ошибок**: Все ошибки логируются, обработка продолжается для остальных файлов
4. **Вывод результатов**: JSON выводится в консоль и записывается в лог