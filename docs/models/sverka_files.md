# Документация по модели `amanat.sverka_files`

## Описание
Модель `amanat.sverka_files` предназначена для хранения и управления файлами сверок, связанными с контрагентами. Используется для организации выгрузки и хранения Excel-файлов сверок, а также для связи с вложениями Odoo (`ir.attachment`).

## Основные поля
- **name** (`Char`): Наименование файла сверки. Используется для отображения и поиска.
- **contragent_id** (`Many2one`): Контрагент, к которому относится файл сверки (`amanat.contragent`).
- **attachment_ids** (`One2many`, compute): Вложения, связанные с данной записью. Вычисляется автоматически по связке res_model/res_id.
- **file_attachments** (`Many2many`): Документы (Excel-файлы, PDF и др.), прикреплённые к сверке. Используется для хранения выгруженных файлов сверок.

## Методы
- **_compute_attachments(self)**: Автоматически вычисляет связанные вложения для каждой записи, используя стандартную модель Odoo `ir.attachment`.
  - Пример вызова: вызывается автоматически при отображении поля `attachment_ids`.

## Связи с другими моделями
- `amanat.contragent`: связь через поле `contragent_id`.
- `ir.attachment`: связь через поля `attachment_ids` и `file_attachments`.
- Используется в автоматизации выгрузки сверок (см. методы выгрузки в модели reconciliation).

## Пример использования
```python
# Создание файла сверки для контрагента
sverka = self.env['amanat.sverka_files'].create({
    'name': 'Сверка Иванов.xlsx',
    'contragent_id': contragent_id,
})
# Добавление вложения
attachment = self.env['ir.attachment'].create({
    'name': 'Сверка Иванов.xlsx',
    'type': 'url',
    'url': file_url,
    'res_model': 'amanat.sverka_files',
    'res_id': sverka.id,
})
sverka.file_attachments = [(4, attachment.id)]
```

## Рекомендации по расширению
- Для добавления новых типов вложений используйте стандартные механизмы Odoo attachments.
- Для интеграции с внешними сервисами выгрузки используйте методы, аналогичные `_run_reconciliation_export` в модели reconciliation.
- Для кастомных бизнес-процессов можно добавить дополнительные поля (например, статус сверки, дату загрузки и т.д.). 