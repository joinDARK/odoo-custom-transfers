# Документация по модели amanat.money
## Описание
Модель `amanat.money` предназначена для учета движения денежных средств (контейнеров денег) по ордерам, с поддержкой мультивалютности, роялти, автоматических расчетов остатков и состояния, а также связей со списаниями и сверками.

Эта модель наследуется от: `amanat.base.model`, `mail.thread`, `mail.activity.mixin`

## Поля
- **royalty** (`Boolean`): Признак роялти (True — контейнер роялти)
- **percent** (`Boolean`): Признак процентного контейнера
- **date** (`Date`): Дата движения
- **wallet_id** (`Many2one`): Кошелек. Связь с `amanat.wallet`
- **partner_id** (`Many2one`): Держатель. Связь с `amanat.contragent`
- **currency** (`Selection`): Валюта (`RUB`, `USD`, `USDT`, `EURO`, `CNY`, `AED`, `THB` и их кэше-аналоги). По дефолту `RUB`
- **writeoff_ids** (`One2many`): Списания. Связь с `amanat.writeoff`
- **amount** (`Float`): Сумма движения
- **order_id** (`Many2one`): Ордер. Связь с `amanat.order`
- **state** (`Selection`): Состояние контейнера (`debt` — долг, `positive` — положительный, `empty` — пусто)
- **sum_rub**, **sum_usd**, **sum_usdt**, **sum_cny**, **sum_euro**, **sum_aed**, **sum_thb** и т.д. (`Float`): Суммы по каждой валюте
- **remains** (`Float`, вычисляется): Остаток по контейнеру
- **remains_<валюта>** (remains_rub, remains_usd, ...) (`Float`, вычисляется): Остатки по каждой валюте
- **sum_remains** (`Float`, вычисляется): Сумма всех списаний по контейнеру
- **comment** (`Text`, related): Комментарий из ордера

## Методы
- **@api.depends(...) compute_remains_fields** — Вычисляет остатки по контейнеру, остатки по валютам, сумму списаний. Автоматически обновляет состояние контейнера.
- **_auto_update_state_after_compute** — Автоматически обновляет поле state после пересчета остатков.
- **update_state_based_on_remainder** — Принудительно обновляет состояние контейнера на основе остатка (используется из других моделей).
- **@api.model auto_update_all_states** — Массовое обновление состояния для всех контейнеров (используется как cron job).
- **_get_realtime_fields** — Возвращает список полей для real-time обновлений в списке контейнеров денег.

### Важные детали
- Все поля, кроме названий, должны отслеживаться в `chatter`.
- Все вычисления остатков и состояния происходят автоматически при изменении суммы, валюты или списаний.
- Для корректной работы должны быть заведены все необходимые кошельки, контрагенты и ордера.