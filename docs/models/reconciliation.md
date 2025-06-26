# Документация по модели `amanat.reconciliation`
## Описание
Модель `amanat.reconciliation` предназначена для учета сверок между контрагентами, плательщиками и ордерами, с поддержкой мультивалютности, диапазонов дат, автоматических расчетов эквивалента, интеграции с выгрузкой данных и связей с другими сущностями системы.

Эта модель наследуется от: `amanat.base.model`, `mail.thread`, `mail.activity.mixin`

## Поля
- **date** (`Date`): Дата сверки
- **partner_id** (`Many2one`): Контрагент. Связь с `amanat.contragent`
- **currency** (`Selection`): Валюта (`RUB`, `USD`, `USDT`, `EURO`, `CNY`, `AED`, `THB` и их кэше-аналоги). По дефолту `RUB`
- **sum** (`Float`): Сумма.
- **wallet_id** (`Many2one`): Кошелек. Связь с `amanat.wallet`
- **sender_id** (`Many2many`): Плательщик-отправитель. Связь с `amanat.payer`
- **sender_contragent** (`Many2many`, related): Контрагент отправителя.
- **receiver_id** (`Many2many`): Плательщик-получатель. Связь с `amanat.payer`
- **receiver_contragent** (`Many2many`, related): Контрагент получателя
- **sum_rub**, **sum_usd**, **sum_usdt**, **sum_cny**, **sum_euro**, **sum_aed**, **sum_thb** и т.д. (`Float`): Суммы по каждой валюте
- **rate** (`Float`, related): Курс (из ордера)
- **award** (`Float`, related): % за операцию (из ордера)
- **rko** (`Float`, related): РКО (из ордера)
- **our_percent** (`Float`, related): Наш % за операцию (из ордера)
- **rko_2** (`Float`, related): РКО 2 (из ордера)
- **exchange** (`Float`, вычисляется): К выдаче (по умолчанию равен сумме)
- **order_id** (`Many2many`): Ордера. Связь с `amanat.order`
- **order_comment** (`Text`, related): Комментарий из ордера
- **unload** (`Boolean`): Флаг для выгрузки сверки
- **range** (`Many2one`): Диапазон. Связь с `amanat.ranges`
- **range_reconciliation_date_1 и range_reconciliation_date_2** (`Date`, related): Даты сверки из диапазона
- **range_date_reconciliation** (`Selection`): Флаг сверки по диапазону дат
- **compare_balance_date_1 и compare_balance_date_2** (`Date`, related): Даты сравнения баланса из диапазона
- **status_comparison_1 и status_comparison_2** (`Selection`): Статус сравнения
- **range_date_start и range_date_end** (`Date`, related): Даты начала и конца диапазона
- **status_range** (`Selection`): Статус диапазона
- **rate_id** (`Many2one`): Курс. Связь с `amanat.rates`
- **rate_euro**, **rate_cny**, **rate_rub**, **rate_aed**, **rate_thb**, **rate_usd**, **rate_usdt** (`Float`, related): Курсы валют
- **equivalent** (`Float`): Эквивалент в долларах
- **range_reconciliation_bool** (`Boolean`): Флаг сверки по диапазону

## Методы
- **@api.depends('sum') compute_exchange** — Вычисляет поле exchange (по умолчанию равно сумме).
- **@api.depends(<валютные_суммы>, <курсы>) compute_equivalent** — Вычисляет эквивалент в долларах по всем валютам.
- **write(vals)** — Переопределённый метод записи: реализует автоматическую выгрузку при установке флага unload.
- **@api.model create(vals)** — Переопределённый метод создания: автозаполнение диапазона и курса, автоматическая выгрузка при необходимости.
- **_prepare_reconciliation_export_data(contragent, use_range)** — Готовит данные для экспорта сверок по контрагенту и диапазону.
- **_run_reconciliation_export()** — Основная логика выгрузки сверок (отправка на сервер, создание вложения).
- **_get_realtime_fields** — Возвращает список полей для real-time обновлений (если реализовано).

## Важные детали
- Все автоматические действия (выгрузка, автозаполнение диапазона и курса) происходят при создании или изменении записи, если установлен соответствующий флаг.
- Для корректной работы должны быть заведены все необходимые контрагенты, плательщики, кошельки, диапазоны и курсы.