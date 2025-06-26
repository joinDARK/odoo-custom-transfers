# Документация по модели `amanat.reserve`
## Описание
Модель `amanat.reserve` предназначена для учета валютных резервов между контрагентами, с поддержкой комиссий, роялти, автоматического создания ордеров, денежных движений и сверок.

Эта модель наследуется от: `amanat.base.model`, `mail.thread`, `mail.activity.mixin`.

## Поля
- **name** (`Char`): Номер сделки (генерируется автоматически, только для чтения)
- **status** (`Selection`): Статус (`Открыта`, `Архив`, `Закрыта`). По дефолту `Открыта`
- **today_date** (`Date`): Дата резерва. По дефолту - сегодняшняя дата при создании
- **currency** (`Selection`): Валюта (`RUB`, `RUB КЭШ`, `USD`, `USD КЭШ`, `USDT`, `EURO`, `EURO КЭШ`, `CNY`, `CNY КЭШ`, `AED`, `AED КЭШ`, `THB`, `THB КЭШ`). По дефолту `RUB`
- **amount** (`Float`): Сумма резерва. Округляется до 2-х знаков после запятой
- **sender_id** (`Many2one`): Отправитель. Связь с `amanat.contragent`
- **sender_payer_id** (`Many2one`): Плательщик отправителя. Связь с `amanat.payer`. Также имеет атрибут `domain` где в `amanat.payer.contragents_ids` (плательщиках) есть связанные c `sender_id` (контрагентом)
- **commision_percent_1** (`Float`): Процент комиссии по отправке
- **receiver_id** (`Many2one`): Получатель. Связь с `amanat.contragent`
- **receiver_payer_id** (`Many2one`): Плательщик получателя. Связь с `amanat.payer`. Также имеет атрибут `domain` где в `amanat.payer.contragents_ids` (плательщиках) есть связанные c `receiver_id` (контрагентом)
- **commision_percent_2** (`Float`): Процент комиссии получателя
- **commision_difference** (`Float`, вычисляется): Разница комиссий
- **finally_result** (`Float`, вычисляется): Финальный результат
- **has_royalti** (`Boolean`): Есть ли роялти
- **make_royalti** (`Boolean`): Провести роялти
- **royalty_recipient_1** (`Many2one`): Получатель роялти 1. Связь с `amanat.contragent`
- **royalty_percent_1** (`Float`): Процент роялти 1
- **royalty_amount_1** (`Float`, вычисляется): Сумма роялти 1
- **royalty_recipient_2** (`Many2one`): Получатель роялти 2. Связь с `amanat.contragent`
- **royalty_percent_2** (`Float`): Процент роялти 2
- **royalty_amount_2** (`Float`, вычисляется): Сумма роялти 2
- **order_ids** (`Many2many`): Связанные ордера. Связь с `amanat.order`
- **create_reserve** (`Boolean`): Создать резерв
- **update_reserve** (`Boolean`): Изменить резерв
- **delete_reserve** (`Boolean`): Удалить резерв
- **complete_reserve** (`Boolean`): Провести (закрыть) резерв
- **comment** (`Text`, related): Комментарии из связанных ордеров

## Методы
**@api.onchange('sender_id') onchange_sender_id** — Автоматически выбирает первого плательщика отправителя при изменении отправителя.
**@api.onchange('receiver_id') onchange_receiver_id** — Автоматически выбирает первого плательщика получателя при изменении получателя.
**@api.depends('commision_percent_1', 'commision_percent_2') compute_commission_difference** — Вычисляет разницу комиссий по формуле `commision_percent_1 - commision_percent_2`.
**@api.depends('amount', 'commision_difference') compute_finally_result** — Вычисляет финальный результат по формуле `amount - commision_difference`.
**@api.depends('amount', 'royalty_percent_1') compute_royalty_amount_1** — Вычисляет сумму роялти 1 по формуле `amount * royalty_percent_1`.
**@api.depends('amount', 'royalty_percent_2') compute_royalty_amount_2** — Вычисляет сумму роялти 2 по формуле `amount * royalty_percent_2`.
**write(vals)** — Переопределённый метод записи: автоматизирует создание, проведение, удаление резерва и роялти по флагам.
**_create_reserve_order()** — Создаёт ордер резерва и связанные движения (Money, Reconciliation).
**_calculate_amounts(amount, percent_out, percent_in)** — Возвращает кортеж из двух сумм: после вычета комиссий отправителя и получателя.
**_get_currency_fields(currency, amount)** — Возвращает словарь для валютных полей в Money и Reconciliation.
**_create_money_and_reconciliation(order, partner, amount, sender_payer, receiver_payer)** — Создаёт записи в Money и Reconciliation для указанного ордера.
**_delete_related_records()** — Удаляет все связанные ордера, деньги и сверки.
**_complete_reserve()** — Метод-заглушка для проведения (закрытия) резерва.
**_get_default_wallet()** — Возвращает (или создает) кошелек «Валютный резерв».
**_get_default_wallet_id()** — Возвращает id кошелька «Валютный резерв».
**_process_royalty_distribution()** — Создаёт ордера и движения для роялти.

## Процесс заполнения
1. **Заполнение основных данных**
    - Укажите отправителя, получателя, сумму, валюту, плательщиков, комиссии и т.д.
2. **Создание резерва**
    - Установите флаг Создать (`create_reserve`).
    - После сохранения автоматически вызовется метод `_create_reserve_order`, который создаст ордер и связанные движения.
3. **Проведение роялти** *(если требуется)*
    - Заполните поля получателей роялти и проценты.
    - Установите флаг Провести роялти (`make_royalti`).
    - После сохранения автоматически вызовется метод `_process_royalty_distribution`, который создаст отдельные ордера и движения для роялти.
4. **Проведение (закрытие) резерва**
    - Установите флаг Провести (`complete_reserve`).
    - После сохранения статус резерва изменится на «Закрыта».
5. **Удаление резерва** *(если требуется)*
    - Установите флаг Удалить (`delete_reserve`).
    - После сохранения все связанные ордера, деньги и сверки будут удалены, а резерв переведен в архив.

### Важные детали
- Все автоматические действия (создание, проведение, роялти, удаление) происходят при сохранении записи, если установлен соответствующий флаг.
- Если вы редактируете уже существующий резерв, повторное нажатие флага Создать пересоздаст ордер (старые будут удалены).
- Роялти можно добавить как при создании резерва, так и после — главное, чтобы были заполнены необходимые поля и установлен флаг.
- Для корректной работы должны быть заведены все необходимые контрагенты, плательщики и кошельки.