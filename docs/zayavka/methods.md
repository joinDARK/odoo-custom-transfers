# Про файл methods.py
*P.S. Не за все методы в этом файле я шарю*

В `methods.py` отвечает за обработку и запуск автоматизация. Также в нем определены полезные методы, вот их список:
- `def _create_order(self, vals):` — Создает запись в ордерах
- `def _create_money(self, vals):` — Создает запись в контейнерах
- `def _create_reconciliation(self, vals):` — Создаем запись в сверках
- `def _get_currency_fields(currency, amount):` — Возвращает поле с валютой и суммой для `amanat.money`
- `def _get_reconciliation_currency_fields(currency, amount):` — Возвращает поле с валютой и суммой для `amanat.reconciliation`
- `def _get_first_payer(self, contragent):` — Возвращает первого плательщика из параметра `contragent`

Далее триггеры и вызываемые ими методы для автоматизаций (`<название_поля>: <метод_который_вызывается>, <еще_метод>`):

### def write(self, vals) — Обновление записи
- `fin_entry_check: run_all_fin_entry_automations()` — автоматизация "Вход заявки", которые могут сделать только финики. По сути во входе создаются ордера/контейнера/сверки для основных полей в заявке, а также вознаграждений
- `for_khalida_temp: run_for_khalida_automations()` — автоматизация для линка правил и прайс-листов. Они линкуются по определенным условиям (например чтобы эквивалент заявки в долларх подходил под диапазон суммы правила)
- `send_to_reconciliation: run_all_send_to_reconciliation_automations()` — автоматизация для "Выхода" заявки. В этом случае создаются ордера/контейнера/сверки для всего финансового расчет
- `link_jess_rate: run_link_jess_rate_automation()` — автоматизация, для линка курса Джесс
- `rate_fixation_date: run_link_jess_rate_automation(), run_price_list_automation()` — автоматизация, для линка курса Джесс и для линка прайс-листов. Также меняется статус заявки на `'3. Зафиксирован курс'`
- `swift_received_date: —` — автоматизация для смены статуса заявки на `12. Ждем поступление валюты`
- `swift_attachments: analyze_swift_documents_for_approved_date()` — автоматизация для смены статуса заявки на `12. Ждем поступление валюты`, статуса SWIFT на `'SWIFT получен'`, а также если не указана дата в поле `swift_received_date`, то ставит дату на момент срабатывания автоматизации. Также срабатывает автоматизация для анализа SWIFT
- `deal_closed_date: —` — автоматизация для смены статуса заявки на `21. Заявка закрыта`, статуса SWIFT на `'заявка закрыта'`
- `report_attachments: —` — автоматизация для смены статуса заявки на `21. Заявка закрыта`, статуса SWIFT на `'заявка закрыта'`, а также если не указана дата в поле `deal_closed_date`, то ставит дату на момент срабатывания автоматизации
- `rate_field: —` — автоматизация для смены статуса заявки на `3. Зафиксирован курс` а также ставит в поле `rate_fixation_date` дату на момент срабатывания автоматизации
- `zayavka_attachments: zayavka_analyse_with_yandex_gpt()` — автоматизация для анализа документа заявления
- `screen_sber_attachments: analyze_screen_sber_images_with_yandex_gpt()` — автоматизация для анализа скрина сбера
- `invoice_attachments: — ` — меняетcя статус заявки на `2. Выставлен инвойс` и статус SWIFT-а на `SWIFT получен`. Также в поле `invoice_date` записываем дату на момент срабатывания автоматизации
- `assignment_attachments: analyze_assignment_with_yandex_gpt(), should_auto_sign_document(attachments[0]), auto_sign_assignment_with_stellar()` — автоматизация по анализу поручения с помощью YandexGPT и методы для подписания поручения
- `assignment_end_attachments: —` — если есть файл в поле `assignment_end_attachments`, то меняем статус заявки на `4. Подписано поручение`
- `cross_return_date: run_return_payment_to_payer()` — автоматизация по возврату платежа (просто создает ордер/контейнер/сверку на сумму заявки)
- `payment_order_date_to_client_account: run_return_with_main_amount()` — автоматизация по возврату основной суммы. Также создает ордера/контейнера/сверки (все автоматизация по возвратам создают ордера/контейнера/сверки), но другие (реализацию методово смотрите в файле [return_automations.py](return_automations.py))
- `payment_order_date_to_client_account_return_all: run_return_with_all_amount_method()` — автоматизация по воврату всей суммы
- `payment_order_date_to_return: run_return_with_partial_payment_of_remuneration_method()` — автоматизация по возврату с частичной оплатой вознаграждения
- `payment_order_date_to_prepayment_of_next: run_return_with_prepayment_of_next_method()` — автоматизация по возврату на предоплату следующего заказа
- `supplier_currency_paid_date_again_1: run_return_with_subsequent_payment_method(), run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission), rec.supplier_currency_paid_date_again_1, rec.payment_date_again_1)` — автоматизация по возврату с последующей оплатой. Далее будет повторяться для полей `supplier_currency_paid_date_again_2`, `supplier_currency_paid_date_again_3`, `supplier_currency_paid_date_again_4`, `supplier_currency_paid_date_again_5` (метод `def run_return_with_subsequent_payment_method_new_subagent(self, new_amount, date, date2)`)

### def create(self, vals) — Создание записи
Здесь повторяются все автоматизации, что и в `write`