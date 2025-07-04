# Документация по абстрактной модели `amanat.base.model`

## Описание
`amanat.base.model` — абстрактная модель, от которой наследуются все основные бизнес-модели Amanat. Реализует:
- Логирование действий (создание, изменение, удаление) через модель `amanat.activity`.
- Поддержку real-time обновлений (методы для получения и отправки данных по websockets/шине).
- Унифицированные методы для открытия форм, получения полей для real-time, логирования изменений и отправки уведомлений.

## Основные методы
- **open_form(self)**: Открывает форму текущей записи (возвращает dict для ir.actions.act_window).
- **_should_log(self)**: Проверяет, нужно ли логировать действие (например, не логируются действия с логами).
- **_get_realtime_fields(self)**: Возвращает список полей для real-time обновлений. Можно переопределять в дочерних моделях для расширения.
- **_get_record_data_for_realtime(self, record)**: Получает данные записи для real-time (преобразует Many2one в читабельный формат).
- **_send_realtime_notification(self, action, changed_fields=None)**: Отправляет уведомление о событии (создание, изменение, удаление) для real-time интерфейса.
- **_log_activity(self, action, changes=None)**: Логирует действие (создание, изменение, удаление) в модель `amanat.activity`.
- **create(self, vals_list)**: Переопределён для логирования и real-time уведомлений при создании.
- **write(self, vals)**: Переопределён для логирования изменений и отправки real-time уведомлений.
- **unlink(self)**: Переопределён для логирования удаления и отправки real-time уведомлений.

## Best practices по наследованию
- Наследуйте свои модели от `amanat.base.model`, чтобы автоматически получить логирование и real-time.
- Для расширения логики логирования переопределяйте `_should_log` и `_log_activity`.
- Для поддержки новых real-time полей переопределяйте `_get_realtime_fields`.
- Для интеграции с внешними сервисами используйте `_send_realtime_notification`.

## Пример расширения
```python
class MyModel(models.Model, AmanatBaseModel):
    _name = 'amanat.my_model'
    _inherit = ['amanat.base.model']
    _description = 'Моя модель'

    name = fields.Char()
    state = fields.Selection([...])

    def _get_realtime_fields(self):
        fields = super()._get_realtime_fields()
        fields.append('my_custom_field')
        return fields
```

## Важно
- Не используйте напрямую для создания записей — только для наследования.
- Все бизнес-модели Amanat должны наследовать этот класс для унификации логирования и real-time. 