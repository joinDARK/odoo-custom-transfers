# Документация по модели amanat.order
## Описание
Модель `amanat.order` предназначена для учета ордеров (переводов, оплат, роялти и др.) между контрагентами, с поддержкой различных сценариев движения средств, автоматических расчетов, связей с другими сущностями системы (заявки, инвестиции, конвертации, резервы и др.).

Эта модель наследуется от: `amanat.base.model`, `mail.thread`, `mail.activity.mixin`

## Поля
- **name** (`Char`): ID ордера. Генерируется автоматически, только для чтения
- **date** (`Date`): Дата ордера. По умолчанию — сегодняшняя дата
- **type** (`Selection`): Тип ордера (`Перевод`, `Оплата`, `Роялти`)
- **transfer_id** (`Many2many`): Переводы. Связан с `amanat.transfer`
- **money_ids** (`One2many`): Денежные контейнеры. Связан с `amanat.money`
- **sverka_ids** (`Many2many`): Сверки. Связан с `amanat.reconciliation`
- **partner_1_id** (`Many2one`): Контрагент 1. Связан с `amanat.contragent`
- **payer_1_id** (`Many2one`): Плательщик 1. Связан с `amanat.payer`
- **wallet_1_id** (`Many2one`): Кошелек 1. Связан с `amanat.wallet`
- **partner_2_id** (`Many2one`): Контрагент 2. Связан с `amanat.contragent`
- **payer_2_id** (`Many2one`): Плательщик 2. Связан с `amanat.payer`
- **wallet_2_id** (`Many2one`): Кошелек 2. Связан с `amanat.wallet`
- **currency** (`Selection`): Валюта (`RUB`, `USD`, `USDT`, `EURO`, `CNY`, `AED`, `THB` и их кэше-аналоги)
- **amount** (`Float`): Сумма ордера
- **rate** (`Float`): Курс
- **operation_percent** (`Float`): % за операцию
- **our_percent** (`Float`): Наш % за операцию
- **rko** (`Float`, вычисляется): РКО (расчетно-кассовое обслуживание)
- **amount_1** (`Float`, вычисляется): Сумма 1 (после вычета комиссии)
- **rko_2** (`Float`, вычисляется): РКО 2 (по нашему проценту)
- **amount_2** (`Float`, вычисляется): Сумма 2 (после вычета нашего процента)
- **total** (`Float`, вычисляется): Итоговая сумма
- **comment** (`Text`): Комментарий
- **is_confirmed** (`Boolean`): Провести
- **status** (`Selection`): Статус (`Черновик`, `Подтверждено`, `Выполнено`)
- **zayavka_ids** (`Many2many`): Заявки. Связан с `amanat.zayavka`
- **money** (`Float`): Деньги
- **investment** (`Many2many`): Инвестиции. Связан с `amanat.investment`
- **gold** (`Many2many`): Золото. Связан с `amanat.gold_deal`
- **conversion_ids** (`Many2many`): Конвертации. Связан с `amanat.conversion`
- **cross_from** (`Boolean`, вычисляется): Кросс-конверт (из конвертации)
- **cross_rate** (`Float`, вычисляется): Кросс-курс (из конвертации)
- **currency_from_conv** (`Selection`, вычисляется): Валюта из конвертации
- **currency_to_copy** (`Selection`, вычисляется): В какую валюту (из конвертации)
- **cross_currency** (`Selection`, вычисляется): Кросс-валюта (из конвертации)
- **cross_calc** (`Float`, вычисляется): Подсчет кросса
- **amount_after_conv** (`Float`, вычисляется): Сумма после конвертации
- **partner_gold** (`Many2many`): Партнеры золото. Связан с `amanat.partner_gold`
- **write_off** (`Float`): Списания
- **rollup_write_off** (`Float`, вычисляется): Роллап списания (сумма всех списаний по контейнерам)
- **remaining_debt** (`Float`, вычисляется): Остаток долга
- **reserve_ids** (`Many2many`): Валютные резервы. Связан с `amanat.reserve`
- **currency_from_zayavka** (`Selection`, вычисляется): Валюта из заявки
- **converted_sum_from_zayavka** (`Float`, вычисляется): Сумма после конвертации из заявки

### Важные детали
- Все поля, кроме названий, должны отслеживаться в `chatter`.
- Все вычисления происходят автоматически при изменении соответствующих полей.
- Для корректной работы должны быть заведены все необходимые контрагенты, плательщики, кошельки и связанные сущности.