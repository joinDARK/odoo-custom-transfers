# Документация по модели `amanat.reconciliation`

## Описание
Модель `amanat.reconciliation` предназначена для учета сверок между контрагентами, плательщиками и ордерами. Поддерживает мультивалютность, автоматические вычисления эквивалента, интеграцию с выгрузкой данных, работу с диапазонами дат и тесно связана с другими сущностями системы (кошельки, курсы, диапазоны, ордера и др.).

Модель наследует: `amanat.base.model`, `mail.thread`, `mail.activity.mixin`

## Поля
- **date** (`Date`): Дата сверки
- **partner_id** (`Many2one`): Контрагент (`amanat.contragent`)
- **currency** (`Selection`): Валюта (RUB, USD, USDT, EURO, CNY, AED, THB и их кэше-аналоги). По умолчанию RUB
- **sum** (`Float`): Сумма сверки
- **wallet_id** (`Many2one`): Кошелек (`amanat.wallet`)
- **sender_id** (`Many2many`): Плательщик-отправитель (`amanat.payer`)
- **sender_contragent** (`Many2many`, related): Контрагент отправителя (через sender_id)
- **receiver_id** (`Many2many`): Плательщик-получатель (`amanat.payer`)
- **receiver_contragent** (`Many2many`, related): Контрагент получателя (через receiver_id)
- **sum_rub**, **sum_usd**, **sum_usdt**, **sum_cny**, **sum_euro**, **sum_aed**, **sum_thb** (`Float`): Суммы по каждой валюте
- **sum_rub_cashe**, **sum_usd_cashe**, **sum_cny_cashe**, **sum_euro_cashe**, **sum_aed_cashe**, **sum_thb_cashe** (`Float`): Суммы по каждой валюте в кэше
- **rate** (`Float`, related): Курс (из ордера)
- **award** (`Float`, related): % за операцию (из ордера)
- **rko** (`Float`, related): РКО (из ордера)
- **our_percent** (`Float`, related): Наш % за операцию (из ордера)
- **rko_2** (`Float`, related): РКО 2 (из ордера)
- **exchange** (`Float`, compute): К выдаче (вычисляется, по умолчанию равен sum)
- **order_id** (`Many2many`): Ордера (`amanat.order`)
- **order_comment** (`Text`, related): Комментарий из ордера
- **range** (`Many2one`): Диапазон (`amanat.ranges`)
- **range_reconciliation_date_1**, **range_reconciliation_date_2** (`Date`, related): Даты сверки из диапазона
- **range_date_reconciliation** (`Selection`): Флаг сверки по диапазону дат
- **compare_balance_date_1**, **compare_balance_date_2** (`Date`, related): Даты сравнения баланса из диапазона
- **status_comparison_1**, **status_comparison_2** (`Selection`): Статус сравнения
- **range_date_start**, **range_date_end** (`Date`, related): Даты начала и конца диапазона
- **status_range** (`Selection`): Статус диапазона
- **rate_id** (`Many2one`): Курс (`amanat.rates`)
- **rate_euro**, **rate_cny**, **rate_rub**, **rate_aed**, **rate_thb**, **rate_usd**, **rate_usdt** (`Float`, related): Курсы валют
- **equivalent** (`Float`, compute): Эквивалент в долларах (вычисляется по всем валютам и их курсам)
- **range_reconciliation_bool** (`Boolean`): Флаг сверки по диапазону
- **create_Reconciliation**, **royalti_Reconciliation** (`Boolean`): Временные/устаревшие поля (помечены как TODO к удалению)

## Основные методы
- **_compute_exchange** (`@api.depends('sum')`): Вычисляет поле exchange (по умолчанию равно sum)
- **_compute_equivalent** (`@api.depends(<валютные_суммы>, <курсы>)`): Вычисляет эквивалент в долларах по всем валютам
- **write(vals)**: Переопределённый метод записи. Реализует автоматическую выгрузку при установке флага unload (если поле реализовано)
- **create(vals)**: Переопределённый метод создания. Автоматически подставляет диапазон и курс, если не указаны, и запускает выгрузку при необходимости
- **_prepare_reconciliation_export_data(contragent, use_range)**: Готовит данные для экспорта сверок по контрагенту и диапазону (формирует структуру для выгрузки)
- **_run_reconciliation_export()**: Основная логика выгрузки сверок (отправка на сервер, создание вложения, запись в amanat.sverka_files)
- **action_send_selected_to_server()**: Массовое действие для отправки выбранных записей на сервер

## Важные детали и автоматизация
- При создании записи, если не указан диапазон или курс, автоматически подставляются значения с id=1 из соответствующих моделей
- При установке флага выгрузки (unload) автоматически запускается экспорт сверки на внешний сервер, создаётся вложение и запись в amanat.sverka_files
- Эквивалент в долларах вычисляется по всем валютам и их курсам, включая кэше-аналоги
- Для корректной работы должны быть заведены все необходимые контрагенты, плательщики, кошельки, диапазоны и курсы
- В модели реализована поддержка трекинга изменений (tracking=True) для большинства полей

## Связанные модели
- `amanat.contragent` — контрагенты
- `amanat.payer` — плательщики
- `amanat.wallet` — кошельки
- `amanat.order` — ордера
- `amanat.ranges` — диапазоны дат
- `amanat.rates` — курсы валют
- `amanat.sverka_files` — файлы сверок (для выгрузки)

## Пример использования
- Создание сверки с автоматическим заполнением диапазона и курса:
  ```python
  self.env['amanat.reconciliation'].create({
      'date': fields.Date.today(),
      'partner_id': partner_id,
      'currency': 'usd',
      'sum': 1000,
      'wallet_id': wallet_id,
  })
  ```
- Массовая выгрузка выбранных сверок:
  ```python
  records.action_send_selected_to_server()
  ```