# Документация по модели `amanat.partner_gold`

## Описание
Модель `amanat.partner_gold` предназначена для учета партнеров в сделках с золотом, хранения информации о закупке, продаже, расчетах расходов, прибыли, роялти и автоматизации денежных переводов между партнерами и основной сделкой.

Эта модель наследуется от: `amanat.base.model`, `mail.thread`, `mail.activity.mixin`

## Поля
- **name** (`Char`): ID Партнера. Генерируется автоматически, только для чтения
- **deal_date** (`Date`): Дата сделки. По умолчанию текущая дата
- **partner_id** (`Many2one`): Партнер. Связь с `amanat.contragent`
- **payer_id** (`Many2one`): Плательщик. Связь с `amanat.payer`. Domain: только плательщики, связанные с выбранным партнером
- **currency_id** (`Many2one`): Валюта. По умолчанию `USD`
- **price_per_oz** (`Monetary`): Цена за oz в $
- **discount_premium** (`Float`): Дисконт/премия (в процентах)
- **bank_rate** (`Float`): Курс банка
- **purchase_price_rub_per_gram** (`Float`, вычисляемое): Цена закупки, руб/гр
- **pure_weight** (`Float`): Чистый вес, гр
- **amount_rub** (`Float`, вычисляемое): Сумма, руб
- **pure_weight_oz** (`Float`, вычисляемое): Чистый вес OZ. Округляется до 3-х знаков после запятой
- **dollar_rate_formula** (`Float`, вычисляемое): Курс $ на дату покупки (формула)
- **dollar_rate** (`Float`): Курс $ на дату покупки (ручной ввод). Округляется до 2-х знаков после запятой
- **purchase_amount_dollar** (`Float`, вычисляемое): Сумма закупа, $ (по формуле или ручному курсу)
- **sale_date** (`Date`): Дата продажи
- **initial_price_per_oz** (`Float`): Изначальная цена $/OZ
- **sale_discount_per_oz** (`Float`): Дисконт продажи $/OZ
- **sale_price_per_oz** (`Float`, вычисляемое): Цена продажи $/OZ
- **aed_rate** (`Float`): Курс AED. По умолчанию 3.673. Округляется до 3-х знаков после запятой
- **sale_amount_aed** (`Float`, вычисляемое): Сумма продажи AED
- **usdt_rate** (`Float`): Курс USDT. Округляется до 5-ти знаков после запятой
- **purchase_usdt** (`Float`, вычисляемое): Покупка USDT
- **bank_percent** (`Float`): %Банк. По умолчанию 0.0012
- **bank_amount** (`Float`, вычисляемое): Банк сумма. Округляется до 3-x знаков после запятой
- **service_percent** (`Float`): %Услуга. По умолчанию 0.005
- **service_amount** (`Float`, вычисляемое): Услуга сумма. Округляется до 3-x знаков после запятой
- **bank_kb_percent** (`Float`): %Банк КБ. По умолчанию 0.001.
- **bank_kb_amount** (`Float`, вычисляемое): Банк КБ сумма. Округляется до 3-x знаков после запятой
- **courier_percent** (`Float`): %Курьер. По умолчанию 0.0015. Округляется до 5-ти знаков после запятой
- **courier_amount** (`Float`, вычисляемое): Курьер сумма. Округляется до 3-х знаков после запятой
- **total_extra_expenses** (`Float`, вычисляемое): Доп расходы
- **overall_pure_weight** (`Float`, вычисляемое): Чистый вес общий
- **extra_expenses_computed** (`Float`, вычисляемое): Дополнительные расходы (расчет).
- **gold_deal_ids** (`Many2many`): Золото сделка. Связь с `amanat.gold_deal`
- **total_expenses** (`Float`, вычисляемое): Всего расходы
- **overall_amount** (`Float`, вычисляемое): Общая сумма
- **profit** (`Float`, вычисляемое): Прибыль
- **deal_percentage** (`Float`, вычисляемое): Процент сделки
- **final_rate** (`Float`, вычисляемое): Курс итог
- **order_ids** (`Many2many`): Ордеры. Связь с `amanat.order`
- **has_royalty** (`Boolean`): Есть роялти?
- **royalty_recipient_id** (`Many2one`): Получатель роялти. Связь с `amanat.contragent`
- **first_percent** (`Float`): % первого
- **royalty_amount_1** (`Float`, вычисляемое): Сумма роялти 1
- **payment_date** (`Date`): Дата оплаты. По дефолтку сегодняшняя дата
- **conduct_gold_transfer** (`Boolean`): Провести перевод на золото
- **wallet_id** (`Many2one`): Кошелек для перевода. Связь с `amanat.wallet`
- **lookup_pure_weight** (`Float`, вычисляемое): Чистый вес, гр (Lookup)
- **lookup_invoice_amount** (`Float`, вычисляемое): Сумма по инвойсу (Lookup)
- **partner_percentage** (`Float`, вычисляемое): Процент партнера от всего закупа
- **partner_invoice_amount** (`Float`, вычисляемое): Сумма партнера от инвойса

## Методы
- **@api.onchange('partner_id') onchange_partner_id** — Автоматически выбирает первого плательщика при изменении партнера.
- **@api.depends('price_per_oz', 'bank_rate', 'discount_premium') compute_purchase_price_rub_per_gram** — Вычисляет цену закупки, руб/гр.
- **@api.depends('pure_weight', 'purchase_price_rub_per_gram') compute_amount_rub** — Вычисляет сумму в рублях.
- **@api.depends('pure_weight') compute_pure_weight_oz** — Вычисляет чистый вес в унциях.
- **@api.depends('bank_rate', 'discount_premium') compute_dollar_rate_formula** — Вычисляет формульный курс доллара.
- **@api.depends('amount_rub', 'dollar_rate', 'dollar_rate_formula') compute_purchase_amount_dollar** — Вычисляет сумму закупа в долларах.
- **@api.depends('initial_price_per_oz', 'sale_discount_per_oz') compute_sale_price_per_oz** — Вычисляет цену продажи $/OZ.
- **@api.depends('sale_price_per_oz', 'pure_weight_oz', 'aed_rate') compute_sale_amount_aed** — Вычисляет сумму продажи AED.
- **@api.depends('sale_amount_aed', 'usdt_rate') compute_purchase_usdt** — Вычисляет сумму покупки USDT.
- **@api.depends('purchase_amount_dollar', 'bank_percent') compute_bank_amount** — Вычисляет сумму банка.
- **@api.depends('purchase_amount_dollar', 'service_percent') compute_service_amount** — Вычисляет сумму услуги.
- **@api.depends('purchase_amount_dollar', 'bank_kb_percent') compute_bank_kb_amount** — Вычисляет сумму банка КБ.
- **@api.depends('purchase_amount_dollar', 'courier_percent') compute_courier_amount** — Вычисляет сумму курьера.
- **@api.depends('gold_deal_ids.extra_expenses') compute_total_extra_expenses** — Вычисляет дополнительные расходы из связанных сделок.
- **@api.depends('gold_deal_ids.pure_weight_sum') compute_overall_pure_weight** — Вычисляет общий чистый вес из связанных сделок.
- **@api.depends('total_extra_expenses', 'overall_pure_weight', 'pure_weight') compute_extra_expenses** — Вычисляет дополнительные расходы на партнера.
- **@api.depends('purchase_amount_dollar', 'bank_percent', 'service_percent', 'bank_kb_percent', 'courier_percent', 'extra_expenses_computed') compute_total_expenses** — Вычисляет все расходы.
- **@api.depends('purchase_usdt', 'total_expenses') compute_overall_amount** — Вычисляет общую сумму.
- **@api.depends('overall_amount', 'purchase_amount_dollar') compute_profit** — Вычисляет прибыль.
- **@api.depends('profit', 'purchase_amount_dollar') compute_deal_percentage** — Вычисляет процент сделки.
- **@api.depends('amount_rub', 'overall_amount') compute_final_rate** — Вычисляет итоговый курс.
- **@api.depends('amount_rub', 'first_percent') compute_royalty_amount_1** — Вычисляет сумму роялти 1.
- **@api.depends('gold_deal_ids.pure_weight_sum') compute_lookup_pure_weight** — Lookup чистого веса из сделок.
- **@api.depends('gold_deal_ids.invoice_amount') compute_lookup_invoice_amount** — Lookup суммы по инвойсу из сделок.
- **@api.depends('pure_weight', 'lookup_pure_weight') compute_partner_percentage** — Вычисляет процент партнера от всего закупа.
- **@api.depends('lookup_invoice_amount', 'partner_percentage') compute_partner_invoice_amount** — Вычисляет сумму партнера от инвойса.
- **@api.model create(vals)** — Переопределённый метод создания: автозаполняет кошелек "Неразмеченные", запускает автоматизацию перевода на золото при необходимости.
- **write(vals)** — Переопределённый метод записи: запускает автоматизацию перевода на золото при необходимости.
- **_action_conduct_gold_transfer** — Создаёт переводы (RUB и USDT), денежные контейнеры и сверки для партнера, если установлен флаг "Провести перевод на золото".

### Важные детали
- Все вычисляемые поля обновляются автоматически при изменении связанных данных.
- При изменении партнера автоматически выбирается первый доступный плательщик.
- Для корректной работы автоматизации должны быть заведены все необходимые контрагенты, плательщики и кошельки. Если их нет — они будут созданы автоматически.
- Для перевода на золото установите флаг "Провести перевод на золото" (`conduct_gold_transfer`). После сохранения будут созданы все необходимые ордера, денежные движения и сверки.
- При создании записи, если не указан кошелек для перевода, автоматически подставляется кошелек "Неразмеченные".
- Все поля, кроме названий, должны отслеживаться в `chatter`.