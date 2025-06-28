# Документация по модели `amanat.gold_deal`

## Описание
Модель `amanat.gold_deal` предназначена для учета сделок с золотом между контрагентами, с поддержкой мультивалютности, комиссий, автоматического создания ордеров, денежных движений и сверок, а также связей с заявками, ордерами и другими сущностями системы.

Эта модель наследуется от: `amanat.base.model`, `mail.thread`, `mail.activity.mixin`

## Поля
- **name** (`Char`): Номер (ID) сделки. Генерируется автоматически, только для чтения
- **status** (`Selection`): Статус (`Открыта`, `Архив`, `Закрыта`). По дефолту `Открыта`
- **date** (`Date`): Дата
- **currency** (`Selection`): Валюта сделки (`RUB`, `USD`, `USDT`, `EURO`, `CNY`, `AED`, `THB` и их кэше-аналоги)
- **amount** (`Float`): Сумма сделки
- **sender_id** (`Many2one`): Отправитель (контрагент)
- **sender_payer_id** (`Many2one`): Плательщик отправителя
- **receiver_id** (`Many2one`): Получатель (контрагент)
- **receiver_payer_id** (`Many2one`): Плательщик получателя
- **wallet_id** (`Many2one`): Кошелек для сделки
- **order_ids** (`Many2many`): Связанные ордера (amanat.order)
- **zayavka_ids** (`Many2many`): Связанные заявки (amanat.zayavka)
- **commission_percent** (`Float`): Процент комиссии по сделке
- **commission_amount** (`Float`, вычисляется): Сумма комиссии
- **create_gold_deal** (`Boolean`): Флаг для создания ордера по сделке
- **delete_gold_deal** (`Boolean`): Флаг для удаления сделки
- **comment** (`Chat`): Комментарий к сделке
- **partner_ids** (`Many2many`): Партнеры. Связь с `amanat.partner_gold`
- **pure_weight_sum** (`Float`): Чистый вес, гр (Rollup)