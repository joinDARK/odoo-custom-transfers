from odoo import models, fields, api
import logging
from odoo.exceptions import UserError
from datetime import datetime
import pytz

_logger = logging.getLogger(__name__)


class GoldDeal(models.Model):
    _name = "amanat.gold_deal"
    _inherit = ["amanat.base.model", "mail.thread", "mail.activity.mixin"]
    _description = "Золото сделка"

    # 1. ID – формируется с помощью последовательности с префиксом "Сделка №"
    name = fields.Char(
        string="ID",
        readonly=True,
        default=lambda self: "Сделка №"
        + str(self.env["ir.sequence"].next_by_code("amanat.gold_deal.sequence")),
        tracking=True,
    )

    # 2. Статус – выбор из трёх вариантов
    status = fields.Selection(
        [("open", "Открыта"), ("closed", "Закрыта"), ("archived", "Архив")],
        string="Статус",
        default="open",
        tracking=True,
    )

    # 3. Комментарий – однострочное текстовое поле
    comment = fields.Char(string="Комментарий", tracking=True)

    # 4. Дата
    date = fields.Date(string="Дата", tracking=True, default=fields.Date.today)

    # 5. Партнеры – связь один-ко-многим с моделью «Партнеры золото»
    partner_ids = fields.Many2many(
        "amanat.partner_gold",
        relation="amanat_partner_gold_deal_rel",
        column1="gold_deal_id",
        column2="partner_gold_id",
        string="Партнеры",
        tracking=True,
    )

    # 6. Чистый вес, гр (Rollup: сумма поля pure_weight из партнеров)
    pure_weight_sum = fields.Float(
        string="Чистый вес, гр (Rollup)",
        compute="_compute_pure_weight_sum",
        store=True,
        tracking=True,
    )

    # 7. Общая сумма покупки (Rollup: сумма поля amount_rub из партнеров)
    purchase_total_rub = fields.Float(
        string="Общая сумма покупки",
        compute="_compute_purchase_total_rub",
        store=True,
        tracking=True,
    )

    # 8. Сумма закупа в долларах (Rollup: сумма поля purchase_amount_dollar из партнеров)
    purchase_total_dollar = fields.Float(
        string="Сумма закупа в долларах",
        compute="_compute_purchase_total_dollar",
        store=True,
        tracking=True,
    )

    # 9. Расходы (Rollup: сумма поля total_expenses из партнеров)
    expenses = fields.Float(
        string="Расходы", compute="_compute_expenses", store=True, tracking=True
    )

    # 10. Услуга (Rollup: сумма поля service из партнеров)
    service = fields.Float(
        string="Услуга", compute="_compute_service", store=True, tracking=True, digits=(16, 3)
    )

    # 11. Банк сумм (Rollup: сумма поля bank_sum из партнеров)
    bank_sum = fields.Float(
        string="Банк сумм", compute="_compute_bank_sum", store=True, tracking=True, digits=(16, 3)
    )

    # 12. Банк КБ (Rollup: сумма поля bank_kb из партнеров)
    bank_kb = fields.Float(
        string="Банк КБ", compute="_compute_bank_kb", store=True, tracking=True, digits=(16, 3)
    )

    # 13. Курьер (Rollup: сумма поля courier из партнеров)
    courier = fields.Float(
        string="Курьер", compute="_compute_courier", store=True, tracking=True, digits=(16, 3)
    )

    # 14. Общая сумма (Rollup: сумма поля purchase_usdt из партнеров)
    total_amount = fields.Float(
        string="Общая сумма", compute="_compute_total_amount", store=True, tracking=True, digits=(16, 3)
    )

    # 15. Сумма продажи AED (Rollup: сумма поля sale_amount_aed из партнеров)
    sale_amount_aed = fields.Float(
        string="Сумма продажи AED",
        compute="_compute_sale_amount_aed",
        store=True,
        tracking=True,
    )

    # 16. Сумма продажи USDT (Rollup: сумма поля purchase_usdt из партнеров)
    sale_amount_usdt = fields.Float(
        string="Сумма продажи USDT",
        compute="_compute_sale_amount_usdt",
        store=True,
        tracking=True,
    )

    # 17. Дополнительные расходы
    extra_expenses = fields.Float(string="Дополнительные расходы", tracking=True)

    # 18. Курс итог – вычисляется как Общая сумма покупки / Общая сумм
    final_rate = fields.Float(
        string="Курс итог", compute="_compute_final_rate", store=True, tracking=True, digits=(16, 3)
    )

    # 19. Провести вход
    conduct_in = fields.Boolean(string="Провести вход", default=False, tracking=True)

    # 20. Провести выход
    conduct_out = fields.Boolean(string="Провести выход", default=False)

    # 21. Проводка Вита
    vita_posting = fields.Boolean(string="Проводка Вита", default=False, tracking=True)

    # 22. Сверка
    reconciliation = fields.Boolean(string="Сверка", default=False, tracking=True)

    # 23. Перепроводка
    reposting = fields.Boolean(string="Перепроводка", default=False, tracking=True)

    # 24. Пометить на удаление
    mark_for_deletion = fields.Boolean(
        string="Удалить", default=False, tracking=True
    )

    # 25. Сумма по инвойсу
    invoice_amount = fields.Float(string="Сумма по инвойсу", tracking=True)

    # 26. Разница = Общая сумма покупки - Сумма по инвойсу
    difference = fields.Float(
        string="Разница", compute="_compute_difference", store=True, tracking=True
    )

    # 27. Банк – связь с контрагентом банка, который может проводить сделки с золотом
    bank = fields.Many2one(
        "amanat.contragent.gold",
        string="Банк",
        tracking=True,
    )

    # 28. Платежка – связь с выпиской разнос (многие ко многим)
    extract_delivery_ids = fields.Many2many(
        "amanat.extract_delivery",
        string="Платежка",
        domain="[('direction_choice', '=', 'gold_deal')]",  # добавляем домен для фильтрации по золотым сделкам
    )

    # 29. Ордеры – связь с ордерами (многие ко многим)
    order_ids = fields.Many2many(
        "amanat.order",
        "amanat_order_gold_deal_rel",
        "gold_deal_id",
        "order_id",
        string="Ордеры",
        tracking=True,
    )

    # 30. Покупатель – связь с Контрагентами
    buyer_id = fields.Many2one("amanat.contragent", string="Покупатель", tracking=True)

    # 31. Хеш
    hash_flag = fields.Boolean(string="Хеш", default=False, tracking=True)

    # 32. Лог обработки
    log_text = fields.Text(string="Лог обработки")

    # --- Compute методы для Rollup/Formula полей ---

    @api.depends("partner_ids.pure_weight")
    def _compute_pure_weight_sum(self):
        for rec in self:
            rec.pure_weight_sum = sum(rec.partner_ids.mapped("pure_weight"))

    @api.depends("partner_ids.amount_rub")
    def _compute_purchase_total_rub(self):
        for rec in self:
            rec.purchase_total_rub = sum(rec.partner_ids.mapped("amount_rub"))

    @api.depends("partner_ids.purchase_amount_dollar")
    def _compute_purchase_total_dollar(self):
        for rec in self:
            rec.purchase_total_dollar = sum(
                rec.partner_ids.mapped("purchase_amount_dollar")
            )

    @api.depends("partner_ids.total_expenses")
    def _compute_expenses(self):
        for rec in self:
            rec.expenses = sum(rec.partner_ids.mapped("total_expenses"))

    @api.depends("partner_ids.service_amount")
    def _compute_service(self):
        for rec in self:
            rec.service = sum(rec.partner_ids.mapped("service_amount"))

    @api.depends("partner_ids.bank_amount")
    def _compute_bank_sum(self):
        for rec in self:
            rec.bank_sum = sum(rec.partner_ids.mapped("bank_amount"))

    @api.depends("partner_ids.bank_kb_amount")
    def _compute_bank_kb(self):
        for rec in self:
            rec.bank_kb = sum(rec.partner_ids.mapped("bank_kb_amount"))

    @api.depends("partner_ids.courier_amount")
    def _compute_courier(self):
        for rec in self:
            rec.courier = sum(rec.partner_ids.mapped("courier_amount"))

    @api.depends("partner_ids.purchase_usdt")
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.partner_ids.mapped("purchase_usdt"))

    @api.depends("partner_ids.sale_amount_aed")
    def _compute_sale_amount_aed(self):
        for rec in self:
            rec.sale_amount_aed = sum(rec.partner_ids.mapped("sale_amount_aed"))

    @api.depends("partner_ids.purchase_usdt")
    def _compute_sale_amount_usdt(self):
        for rec in self:
            rec.sale_amount_usdt = sum(rec.partner_ids.mapped("purchase_usdt"))

    @api.depends("purchase_total_rub", "total_amount")
    def _compute_final_rate(self):
        for rec in self:
            rec.final_rate = (
                rec.purchase_total_rub / rec.total_amount if rec.total_amount else 0
            )

    @api.depends("purchase_total_rub", "invoice_amount")
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.purchase_total_rub - rec.invoice_amount

    def create_partner(self):
        """Создает нового партнера золота с датой текущей сделки"""
        self.ensure_one()
        
        partner_vals = {
            'deal_date': self.date,
            'gold_deal_ids': [(6, 0, [self.id])],
        }
        partner = self.env['amanat.partner_gold'].create(partner_vals)
        
        # Обновляем связь в текущей сделке
        self.partner_ids = [(4, partner.id)]
        
        return {
            'name': 'Создание партнера золота',
            'type': 'ir.actions.act_window',
            'res_model': 'amanat.partner_gold',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_gold_deal_ids': [(6, 0, [self.id])]},
        }

    @staticmethod
    def _prepare_currency_fields(currency_name: str, amount: float): # TODO доделать метод
        mapping = {
            "RUB": "sum_rub",
            "RUB_CASH": "sum_rub_cash",
            "USD": "sum_usd",
            "USD_CASH": "sum_usd_cash",
            "USDT": "sum_usdt",
            "AED": "sum_aed",
            "CNY": "sum_cny",
            "CNY_CASH": "sum_cny_cash",
            "EURO": "sum_euro",
            "EURO_CASH": "sum_euro_cash",
            "THB": "sum_thb",
            "THB_CASH": "sum_thb_cash",
            # … добавьте другие валюты по аналогии
        }
        field_name = mapping.get(currency_name.upper())
        return {field_name: amount} if field_name else {}

    @api.model
    def create(self, vals):
        rec = super(GoldDeal, self).create(vals)

        if vals.get("conduct_in"):
            _logger.info(
                f"Триггер 'Провести вход' активирован при создании для {rec.name}"
            )
            rec._action_process_gold_deal_input_logic()

        if vals.get("mark_for_deletion"):
            rec._action_delete()
            rec.status = "archived"

        if vals.get("conduct_out"):
            _logger.info(f"Триггер 'Провести выход' активирован при создании для {rec.name}")
            rec._action_process_gold_deal_output_logic()
            rec._action_process_gold_deal_distribution_logic()
            rec._action_process_gold_deal_profit_distribution_logic()
            rec.conduct_out = False
        return rec

    def write(self, vals):
        res = super(GoldDeal, self).write(vals)

        for rec in self:
            # Триггер на "Провести вход"
            if vals.get("conduct_in") and rec.conduct_in:
                _logger.info(f"Триггер 'Провести вход' активирован для {rec.name}")
                rec._action_process_gold_deal_input_logic()
                rec.conduct_in = False

            # Обработка пометки на удаление
            if vals.get("mark_for_deletion"):
                rec._action_delete()
                rec.status = "archived"
                rec.mark_for_deletion = False

            # Триггер на "Провести выход"
            if vals.get("conduct_out") and rec.conduct_out:
                _logger.info(f"Триггер 'Провести выход' активирован для {rec.name}")
                rec._action_process_gold_deal_output_logic()
                rec._action_process_gold_deal_distribution_logic()
                rec._action_process_gold_deal_profit_distribution_logic()
                rec.conduct_out = False

            if 'extract_delivery_ids' in vals and rec.extract_delivery_ids:
                _logger.info(f"Изменено поле 'Платежка' для сделки: {rec.name}")
                rec._action_process_gold_deal_payment_logic()

        return res

    def _action_delete(self):
        for rec in self:
            for order in rec.order_ids:
                order.money_ids.unlink()
                order.sverka_ids.unlink()
                order.unlink()
            rec.order_ids = [(5, 0, 0)]
            rec.mark_for_deletion = False

    def _append_log(self, message):
        """Добавляет запись в лог с московским временем, новые записи сверху, максимум 10 строк"""
        tz = pytz.timezone('Europe/Moscow')
        now_str = datetime.now(tz).strftime('%d.%m.%Y %H:%M:%S')
        log_line = f"[{now_str}] {message}"
        log_lines = (self.log_text or '').split('\n')
        log_lines = [line for line in log_lines if line.strip()]
        log_lines = [log_line] + log_lines  # новая запись сверху
        log_lines = log_lines[:10]
        self.write({'log_text': '\n'.join(log_lines)})

    # "Золото вход" контейнеры
    def _action_process_gold_deal_input_logic(self):
        self.ensure_one()  # Убедимся, что работаем с одной записью
        _logger.info(f"Начало обработки 'Вход в сделку Золото' для: {self.name}")
        self._append_log("[Автоматизация] Проведен вход в сделку.")

        # 0. Предварительная очистка (как в Airtable)
        # Эта часть вызывается из write или кнопки, которая сначала вызывает _action_delete
        # Если этот метод вызывается напрямую, и нужна очистка - раскомментируйте:
        if self.order_ids:
           _logger.info(f"Найдены существующие ордера для {self.name}, начинаем очистку...")
           self._action_delete() # Вызываем ваш существующий метод очистки

        ContragentModel = self.env[
            "amanat.contragent"
        ]  # Замените на имя вашей модели контрагентов
        PayerModel = self.env[
            "amanat.payer"
        ]  # Замените на имя вашей модели плательщиков
        WalletModel = self.env[
            "amanat.wallet"
        ]  # Замените на имя вашей модели кошельков
        OrderModel = self.env["amanat.order"]  # Замените на имя вашей модели ордеров
        MoneyModel = self.env["amanat.money"]  # Замените на имя вашей модели денег
        VerificationModel = self.env[
            "amanat.reconciliation"
        ]  # Замените на имя вашей модели сверки
        # CurrencyModel = self.env['res.currency']

        # 1. Получение основных данных из текущей сделки
        deal_date = self.date
        if not deal_date:
            raise UserError("Дата не указана в сделке 'Золото'.")

        if not self.partner_ids:
            raise UserError(f"Нет партнеров для создания ордеров в сделке: {self.name}")

        # 2. Поиск необходимых справочных записей
        # Контрагенты
        gold_contragent = ContragentModel.search([("name", "=", "Золото")], limit=1)
        bank_gold_contragent = self.bank.contragent_id

        if not bank_gold_contragent:
            raise UserError(f"Не найден контрагент банка для сделки: {self.name}")

        # Создаем контрагентов, если они не найдены
        if not gold_contragent:
            gold_contragent = ContragentModel.create({
                "name": "Золото",
            })
            _logger.info("Создан контрагент 'Золото'")

        # Кошельки
        gold_wallet = WalletModel.search([("name", "=", "Золото")], limit=1)
        if not gold_wallet:
            gold_wallet = WalletModel.create({
                "name": "Золото",
            })
            _logger.info("Создан кошелек 'Золото'")

        # Плательщики
        gold_payer = PayerModel.search([("name", "=", "Золото")], limit=1)
        bank_gold_payer = self.bank.contragent_id.payer_ids[0]

        # Создаем плательщиков и связываем с контрагентами, если они не найдены
        if not gold_payer:
            gold_payer = PayerModel.create({
                "name": "Золото",
                "contragents_ids": [(6, 0, [gold_contragent.id])]
            })
            # Обновляем связь с обратной стороны
            gold_contragent.write({
                "payer_ids": [(6, 0, [gold_payer.id])]
            })
            _logger.info("Создан плательщик 'Золото' и связан с контрагентом 'Золото'")

        if not bank_gold_payer:
            bank_gold_payer = PayerModel.create({
                "name": bank_gold_contragent.name,
                "contragents_ids": [(6, 0, [bank_gold_contragent.id])]
            })
            # Обновляем связь с обратной стороны
            bank_gold_contragent.write({
                "payer_ids": [(6, 0, [bank_gold_payer.id])]
            })
            _logger.info(f"Создан плательщик '{bank_gold_contragent.name}' и связан с контрагентом '{bank_gold_contragent.name}'")

        total_rub_amount_for_vita_order = 0.0
        created_orders_for_deal = []

        # 3. Создание ордеров для каждого партнера
        for partner_gold_record in self.partner_ids:
            # partner_gold_record - это запись из 'amanat.partner_gold'

            # Контрагент партнера (предположим, поле называется 'partner_contragent_id' в 'amanat.partner_gold'
            # и это Many2one к 'amanat.contragent')
            if (
                not hasattr(partner_gold_record, "partner_id")
                or not partner_gold_record.partner_id
            ):
                raise UserError(
                    f"Не найден контрагент для партнера: {partner_gold_record.display_name} в сделке {self.name}"
                )
            partner_contragent = partner_gold_record.partner_id

            # Плательщик партнера
            # В Airtable: specifiedPayerArray = partnerRecord.getCellValue("Плательщик")
            # contragentPayer = specifiedPayer ? ... : payersRecords.records.find(r => r.name === contragent.name);
            # Предположим, в 'amanat.partner_gold' есть поле 'specified_payer_id' (M2O к 'модель.плательщик')
            # и если оно не заполнено, то ищем плательщика по имени контрагента партнера.
            partner_payer = None
            if (
                hasattr(partner_gold_record, "payer_id")
                and partner_gold_record.payer_id
            ):
                partner_payer = partner_gold_record.payer_id
            else:
                # Ищем плательщика по имени контрагента партнера
                partner_payer = PayerModel.search(
                    [("name", "=", partner_contragent.name)], limit=1
                )

            if not partner_payer:
                _logger.error(
                    f"Не найден плательщик для партнера: {partner_contragent.name} (ID: {partner_contragent.id}) в сделке {self.name}"
                )
                continue

            # Сумма партнера от инвойса (предположим, поле 'amount_rub_invoice' в 'amanat.partner_gold')
            # В Airtable: amountRUB = partnerRecord.getCellValue("Сумма партнера от инвойса");
            # В вашей модели 'amanat.gold_deal' есть _compute_purchase_total_rub, которое суммирует 'amount_rub' из 'partner_ids'.
            # Будем считать, что в 'amanat.partner_gold' есть поле 'amount_rub_contribution' или аналогичное.
            # ИЛИ, если 'Сумма партнера от инвойса' это 'amount_rub' из модели партнера:
            partner_amount_rub = getattr(
                partner_gold_record, "amount_rub", 0.0
            )  # Замените 'amount_rub' на актуальное поле в amanat.partner_gold
            if (
                partner_amount_rub is None or partner_amount_rub <= 0
            ):  # Airtable проверял на null
                _logger.error(
                    f"Нулевая или отсутствующая сумма для партнера: {partner_contragent.name} в сделке {self.name}"
                )
                continue

            _logger.info(
                f"Создание ордера для партнера {partner_contragent.name}, сумма: {partner_amount_rub}"
            )

            # Создаем ордер партнер
            order_vals = {
                "date": deal_date,
                "partner_1_id": partner_contragent.id,
                "payer_1_id": partner_payer.id,
                "partner_2_id": gold_contragent.id,
                "payer_2_id": gold_payer.id,
                "amount": partner_amount_rub,
                "type": "transfer",  # Предположим, поле 'order_type' и значение 'transfer' для "Перевод"
                "currency": "rub",
                "gold": [(6, 0, [self.id])],  # Связь с текущей сделкой 'Золото'
                "partner_gold": [
                    (4, partner_gold_record.id)
                ],  # Связь с записью 'Партнеры золото'
                "wallet_1_id": gold_wallet.id,  # "Кошелек 1": [{ id: goldWallet.id }]
                "wallet_2_id": gold_wallet.id,  # "Кошелек 2": [{ id: goldWallet.id }]
                "comment": "Вход в сделку Золото",  # Добавляем комментарий сразуи
            }
            partner_order = OrderModel.create(order_vals)
            created_orders_for_deal.append(partner_order.id)
            _logger.info(
                f"Создан ордер партнера: {partner_order.name if hasattr(partner_order, 'name') else partner_order.id}"
            )

            # Создаем положительный денежный контейнер для партнера
            money_positive_vals = {
                "date": deal_date,
                "partner_id": partner_contragent.id,  # "Держатель"
                "currency": "rub",
                "amount": partner_amount_rub,
                "state": "positive",  # Предположим, поле 'state' и значение 'positive' для "Положительный"
                "wallet_id": gold_wallet.id,
                "order_id": partner_order.id,  # Связь с созданным ордером
                # Используем ваш метод для полей сумм
            }
            money_positive_vals.update(
                self._prepare_currency_fields("RUB", partner_amount_rub)
            )
            MoneyModel.create(money_positive_vals)
            _logger.info(
                f"Создан положительный денежный контейнер для {partner_contragent.name}"
            )

            # Создаем сверку для стороны партнера
            verif_partner_vals = {
                "date": deal_date,
                "partner_id": partner_contragent.id,
                "currency": "rub",
                "sender_id": [(6, 0, [partner_payer.id])],  # "Отправитель"
                "receiver_id": [(6, 0, [gold_payer.id])],  # "Получатель"
                "order_id": [(6, 0, [partner_order.id])],
                "wallet_id": gold_wallet.id,
                "sum": partner_amount_rub,
            }
            verif_partner_vals.update(
                self._prepare_currency_fields("RUB", partner_amount_rub)
            )
            VerificationModel.create(verif_partner_vals)
            _logger.info(f"Создана сверка для {partner_contragent.name}")

            total_rub_amount_for_vita_order += partner_amount_rub

        # 4. Создаем финальный ордер
        if total_rub_amount_for_vita_order > 0:
            _logger.info(
                f"Создание финального ордера Золото -> {bank_gold_contragent.name}, общая сумма: {total_rub_amount_for_vita_order}"
            )
            final_order_vals = {
                "date": deal_date,
                "partner_1_id": gold_contragent.id,
                "payer_1_id": gold_payer.id,
                "partner_2_id": bank_gold_contragent.id,
                "payer_2_id": bank_gold_payer.id,
                "amount": total_rub_amount_for_vita_order,
                "type": "transfer",
                "currency": "rub",
                "gold": [(6, 0, [self.id])],
                "wallet_1_id": gold_wallet.id,
                "wallet_2_id": gold_wallet.id,
                "comment": "Вход в сделку Золото",
            }
            final_order = OrderModel.create(final_order_vals)
            created_orders_for_deal.append(final_order.id)
            _logger.info(
                f"Создан финальный ордер: {final_order.name if hasattr(final_order, 'name') else final_order.id}"
            )

            # Создаем долговой денежный контейнер
            money_debt_vals = {
                "date": deal_date,
                "partner_id": bank_gold_contragent.id,
                "currency": "rub",
                "amount": -total_rub_amount_for_vita_order,  # Отрицательная сумма
                "state": "debt",  # Предположим, значение 'debt' для "Долг"
                "wallet_id": gold_wallet.id,
                "order_id": final_order.id,
            }
            money_debt_vals.update(
                self._prepare_currency_fields("RUB", -total_rub_amount_for_vita_order)
            )
            MoneyModel.create(money_debt_vals)
            _logger.info(f"Создан долговой денежный контейнер для {bank_gold_contragent.name}")

            # Создаем сверку для стороны Виты
            verif_vita_vals = {
                "date": deal_date,
                "partner_id": bank_gold_contragent.id,
                "currency": "rub",
                "sender_id": [(6, 0, [gold_payer.id])],
                "receiver_id": [(6, 0, [bank_gold_payer.id])],
                "order_id": [(6, 0, [final_order.id])],
                "wallet_id": gold_wallet.id,
                "sum": -total_rub_amount_for_vita_order,
            }
            verif_vita_vals.update(
                self._prepare_currency_fields("RUB", -total_rub_amount_for_vita_order)
            )
            VerificationModel.create(verif_vita_vals)
            _logger.info(f"Создана сверка для {bank_gold_contragent.name}")
        else:
            _logger.warning(
                f"Общая сумма для финального ордера Золото->{bank_gold_contragent.name} равна нулю или меньше для сделки {self.name}. Финальный ордер не создан."
            )

        # Обновляем поле order_ids в текущей сделке Золото
        if created_orders_for_deal:
            self.order_ids = [(6, 0, created_orders_for_deal)]

        _logger.info(f"Скрипт успешно завершён для сделки: {self.name}!")
        return True

    # "Золото выход" контейнеры
    def _action_process_gold_deal_output_logic(self):
        self.ensure_one()  # Убедимся, что работаем с одной записью
        _logger.info(f"Начало обработки 'Выход из сделки Золото' для: {self.name}")
        self._append_log("[Автоматизация] Проведен выход из сделки.")
        
        # Предварительная очистка (по необходимости)
        # Если требуется удалить предыдущие ордера выхода - добавьте логику очистки
        
        ContragentModel = self.env["amanat.contragent"]
        PayerModel = self.env["amanat.payer"]
        WalletModel = self.env["amanat.wallet"]
        OrderModel = self.env["amanat.order"]
        MoneyModel = self.env["amanat.money"]
        VerificationModel = self.env["amanat.reconciliation"]

        # Проверка наличия партнеров и дат
        if not self.partner_ids:
            raise UserError(f"Нет партнеров для создания ордеров выхода в сделке: {self.name}")
                
        # Используем дату продажи из первого партнера (как в скрипте Airtable)
        sale_date = None
        for partner in self.partner_ids:
            if hasattr(partner, 'sale_date') and partner.sale_date:
                sale_date = partner.sale_date
                break
        
        # Проверка наличия покупателя
        if not self.buyer_id:
            raise UserError(f"Не указан покупатель в сделке: {self.name}")
        
        if not sale_date:
            # Если нет даты продажи, используем текущую дату
            sale_date = fields.Date.today()
        
        # Получение справочных записей
        # Контрагент "Золото"
        gold_contragent = ContragentModel.search([("name", "=", "Золото")], limit=1)
        if not gold_contragent:
            raise UserError("Контрагент 'Золото' не найден.")
        
        # Получаем плательщика для покупателя
        buyer_payer = PayerModel.search([("name", "=", self.buyer_id.name)], limit=1)
        if not buyer_payer:
            raise UserError(f"Не найден плательщик для покупателя: {self.buyer_id.name}")
        
        # Получаем плательщика "Золото"
        gold_payer = PayerModel.search([("name", "=", "Золото")], limit=1)
        if not gold_payer:
            raise UserError("Плательщик 'Золото' не найден.")
        
        # Получаем кошелек "Золото"
        gold_wallet = WalletModel.search([("name", "=", "Золото")], limit=1)
        if not gold_wallet:
            raise UserError("Кошелек 'Золото' не найден.")
        
        # Получаем суммы из сделки
        aed_amount = self.sale_amount_aed
        usdt_amount = self.sale_amount_usdt
        
        if not aed_amount or not usdt_amount:
            raise UserError("Отсутствуют необходимые суммы (AED или USDT) в сделке.")
        
        # Создаем ордер для AED
        order_vals = {
            "date": sale_date,
            "partner_1_id": self.buyer_id.id,
            "payer_1_id": buyer_payer.id,
            "wallet_1_id": gold_wallet.id,
            "partner_2_id": gold_contragent.id,
            "payer_2_id": gold_payer.id,
            "wallet_2_id": gold_wallet.id,
            "gold": [(6, 0, [self.id])],  # Связь с текущей сделкой 'Золото'
            "currency": "aed",
            "amount": aed_amount,
            "type": "transfer",
            "comment": "Выход золото",
        }
        
        order = OrderModel.create(order_vals)
        _logger.info(f"Создан ордер выхода: {order.name if hasattr(order, 'name') else order.id}")
        
        # Добавляем ордер к списку ордеров сделки
        if self.order_ids:
            self.order_ids = [(4, order.id, 0)]
        else:
            self.order_ids = [(6, 0, [order.id])]
        
        # Создаем денежный контейнер для покупателя (AED - положительный)
        money_positive_vals = {
            "date": sale_date,
            "partner_id": self.buyer_id.id,
            "currency": "aed",
            "amount": aed_amount,
            "state": "positive",
            "wallet_id": gold_wallet.id,
            "order_id": order.id,
        }
        money_positive_vals.update(self._prepare_currency_fields("AED", aed_amount))
        MoneyModel.create(money_positive_vals)
        _logger.info(f"Создан положительный денежный контейнер для покупателя в AED")
        
        # Создаем денежный контейнер для Золото (USDT - долговой, отрицательная сумма)
        money_debt_vals = {
            "date": sale_date,
            "partner_id": gold_contragent.id,
            "currency": "usdt",
            "amount": -usdt_amount,
            "state": "debt",
            "wallet_id": gold_wallet.id,
            "order_id": order.id,
        }
        money_debt_vals.update(self._prepare_currency_fields("USDT", -usdt_amount))
        MoneyModel.create(money_debt_vals)
        _logger.info(f"Создан долговой денежный контейнер для Золото в USDT")
        
        # Создаем сверку для покупателя (положительная в AED)
        verif_buyer_vals = {
            "date": sale_date,
            "partner_id": self.buyer_id.id,
            "currency": "aed",
            "sum": aed_amount,
            "sender_id": [(6, 0, [gold_payer.id])],
            "receiver_id": [(6, 0, [buyer_payer.id])],
            "order_id": [(6, 0, [order.id])],
            "wallet_id": gold_wallet.id,
        }
        verif_buyer_vals.update(self._prepare_currency_fields("AED", aed_amount))
        VerificationModel.create(verif_buyer_vals)
        _logger.info("Создана сверка для покупателя в AED (положительная)")
        
        # Создаем сверку для Золото (долговая в USDT)
        verif_gold_vals = {
            "date": sale_date,
            "partner_id": gold_contragent.id,
            "currency": "usdt",
            "sum": -usdt_amount,
            "sender_id": [(6, 0, [gold_payer.id])],
            "receiver_id": [(6, 0, [buyer_payer.id])],
            "order_id": [(6, 0, [order.id])],
            "wallet_id": gold_wallet.id,
        }
        verif_gold_vals.update(self._prepare_currency_fields("USDT", -usdt_amount))
        VerificationModel.create(verif_gold_vals)
        _logger.info("Создана сверка для Золото в USDT (долговая)")
        
        _logger.info(f"Скрипт выхода из сделки успешно завершён для: {self.name}!")
        return True

    def _action_process_gold_deal_distribution_logic(self):
        self.ensure_one()
        _logger.info(f"Начало обработки 'Распределение USDT' для сделки: {self.name}")
        self._append_log("[Автоматизация] Проведено распределение USDT.")
        
        # Поиск необходимых моделей
        ContragentModel = self.env["amanat.contragent"]
        PayerModel = self.env["amanat.payer"]
        WalletModel = self.env["amanat.wallet"]
        OrderModel = self.env["amanat.order"]
        MoneyModel = self.env["amanat.money"]
        VerificationModel = self.env["amanat.reconciliation"]
        
        # Проверка наличия сумм
        if not self.service or not self.bank_sum or not self.bank_kb or not self.courier:
            _logger.warning(f"Отсутствуют одна или несколько сумм для распределения в сделке: {self.name}")
            # Продолжаем с теми суммами, которые есть
        
        # Получаем дату продажи из первого партнера
        sale_date = None
        for partner in self.partner_ids:
            if hasattr(partner, 'sale_date') and partner.sale_date:
                sale_date = partner.sale_date
                break
        
        if not sale_date:
            # Если нет даты продажи, используем текущую дату
            sale_date = fields.Date.today()
        
        # Получаем или создаём контрагенты
        def get_or_create_contragent(name):
            contragent = ContragentModel.search([("name", "=", name)], limit=1)
            if not contragent:
                contragent = ContragentModel.create({"name": name})
                _logger.info(f"Создан контрагент '{name}'")
            return contragent

        gold_contragent = get_or_create_contragent("Золото")
        service_contragent = get_or_create_contragent("Услуга")
        bank_sum_contragent = get_or_create_contragent("Банк сумм")
        bank_kb_contragent = get_or_create_contragent("Банк КБ")
        courier_contragent = get_or_create_contragent("Курьер")

        # Получаем или создаём кошелёк "Золото"
        gold_wallet = WalletModel.search([("name", "=", "Золото")], limit=1)
        if not gold_wallet:
            gold_wallet = WalletModel.create({"name": "Золото"})
            _logger.info("Создан кошелек 'Золото'")

        # Получаем или создаём плательщиков
        def get_or_create_payer(name, contragent):
            payer = PayerModel.search([("name", "=", name)], limit=1)
            if not payer:
                payer = PayerModel.create({
                    "name": name,
                    "contragents_ids": [(6, 0, [contragent.id])]
                })
                contragent.write({
                    "payer_ids": [(6, 0, [payer.id])]
                })
                _logger.info(f"Создан плательщик '{name}' и связан с контрагентом '{name}'")
            return payer

        gold_payer = get_or_create_payer("Золото", gold_contragent)
        service_payer = get_or_create_payer("Услуга", service_contragent)
        bank_sum_payer = get_or_create_payer("Банк сумм", bank_sum_contragent)
        bank_kb_payer = get_or_create_payer("Банк КБ", bank_kb_contragent)
        courier_payer = get_or_create_payer("Курьер", courier_contragent)
        
        # Получаем кошелек
        gold_wallet = WalletModel.search([("name", "=", "Золото")], limit=1)
        if not gold_wallet:
            raise UserError("Не найден кошелек 'Золото'")
        
        # Валюта для всех операций - USDT
        currency = "usdt"
        
        # Обработка каждого контрагента и создание соответствующих ордеров
        
        # 1. Услуга
        if service_contragent and service_payer and self.service:
            try:
                service_amount = self.service
                
                # Создаем ордер
                order_vals = {
                    "date": sale_date,
                    "partner_1_id": gold_contragent.id,
                    "payer_1_id": gold_payer.id,
                    "wallet_1_id": gold_wallet.id,
                    "partner_2_id": service_contragent.id,
                    "payer_2_id": service_payer.id,
                    "wallet_2_id": gold_wallet.id,
                    "gold": [(6, 0, [self.id])],
                    "currency": currency,
                    "amount": service_amount,
                    "type": "transfer",
                    "comment": "Выход золото",
                }
                
                service_order = OrderModel.create(order_vals)
                if self.order_ids:
                    self.order_ids = [(4, service_order.id, 0)]
                else:
                    self.order_ids = [(6, 0, [service_order.id])]
                _logger.info(f"Создан ордер Услуга: {service_order.name if hasattr(service_order, 'name') else service_order.id}")
                
                # Создаем долговой контейнер для Услуги
                money_debt_vals = {
                    "date": sale_date,
                    "partner_id": service_contragent.id,
                    "currency": currency,
                    "amount": -service_amount,
                    "state": "debt",
                    "wallet_id": gold_wallet.id,
                    "order_id": service_order.id,
                }
                money_debt_vals.update(self._prepare_currency_fields("USDT", -service_amount))
                MoneyModel.create(money_debt_vals)
                _logger.info("Создан долговой контейнер для Услуги")
                
                # Создаем положительный контейнер для Золото
                money_positive_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "amount": service_amount,
                    "state": "positive",
                    "wallet_id": gold_wallet.id,
                    "order_id": service_order.id,
                }
                money_positive_vals.update(self._prepare_currency_fields("USDT", service_amount))
                MoneyModel.create(money_positive_vals)
                _logger.info("Создан положительный контейнер для Золото (Услуга)")
                
                # Создаем сверку для контрагента (отрицательная)
                verif_service_vals = {
                    "date": sale_date,
                    "partner_id": service_contragent.id,
                    "currency": currency,
                    "sum": -service_amount,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "receiver_id": [(6, 0, [service_payer.id])],
                    "order_id": [(6, 0, [service_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_service_vals.update(self._prepare_currency_fields("USDT", -service_amount))
                VerificationModel.create(verif_service_vals)
                _logger.info("Создана сверка для Услуги (отрицательная)")
                
                # Создаем сверку для Золото (положительная)
                verif_gold_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "sum": service_amount,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "receiver_id": [(6, 0, [service_payer.id])],
                    "order_id": [(6, 0, [service_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_gold_vals.update(self._prepare_currency_fields("USDT", service_amount))
                VerificationModel.create(verif_gold_vals)
                _logger.info("Создана сверка для Золото (положительная)")
                
            except Exception as e:
                _logger.error(f"Ошибка при создании ордера Услуга: {e}")
        
        # 2. Банк сумм
        if bank_sum_contragent and bank_sum_payer and self.bank_sum:
            try:
                bank_sum_amount = self.bank_sum
                
                # Создаем ордер
                order_vals = {
                    "date": sale_date,
                    "partner_1_id": gold_contragent.id,
                    "payer_1_id": gold_payer.id,
                    "wallet_1_id": gold_wallet.id,
                    "partner_2_id": bank_sum_contragent.id,
                    "payer_2_id": bank_sum_payer.id,
                    "wallet_2_id": gold_wallet.id,
                    "gold": [(6, 0, [self.id])],
                    "currency": currency,
                    "amount": bank_sum_amount,
                    "type": "transfer",
                    "comment": "Выход золото",
                }
                
                bank_sum_order = OrderModel.create(order_vals)
                _logger.info(f"Создан ордер Банк сумм: {bank_sum_order.name if hasattr(bank_sum_order, 'name') else bank_sum_order.id}")
                
                # Создаем долговой контейнер для Банк сумм
                money_debt_vals = {
                    "date": sale_date,
                    "partner_id": bank_sum_contragent.id,
                    "currency": currency,
                    "amount": -bank_sum_amount,
                    "state": "debt",
                    "wallet_id": gold_wallet.id,
                    "order_id": bank_sum_order.id,
                }
                money_debt_vals.update(self._prepare_currency_fields("USDT", -bank_sum_amount))
                MoneyModel.create(money_debt_vals)
                _logger.info("Создан долговой контейнер для Банк сумм")
                
                # Создаем положительный контейнер для Золото
                money_positive_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "amount": bank_sum_amount,
                    "state": "positive",
                    "wallet_id": gold_wallet.id,
                    "order_id": bank_sum_order.id,
                }
                money_positive_vals.update(self._prepare_currency_fields("USDT", bank_sum_amount))
                MoneyModel.create(money_positive_vals)
                _logger.info("Создан положительный контейнер для Золото (Банк сумм)")
                
                # Создаем сверку для контрагента (отрицательная)
                verif_bank_sum_vals = {
                    "date": sale_date,
                    "partner_id": bank_sum_contragent.id,
                    "currency": currency,
                    "sum": -bank_sum_amount,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "receiver_id": [(6, 0, [bank_sum_payer.id])],
                    "order_id": [(6, 0, [bank_sum_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_bank_sum_vals.update(self._prepare_currency_fields("USDT", -bank_sum_amount))
                VerificationModel.create(verif_bank_sum_vals)
                _logger.info("Создана сверка для Банк сумм (отрицательная)")
                
                # Создаем сверку для Золото (положительная)
                verif_gold_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "sum": bank_sum_amount,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "receiver_id": [(6, 0, [bank_sum_payer.id])],
                    "order_id": [(6, 0, [bank_sum_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_gold_vals.update(self._prepare_currency_fields("USDT", bank_sum_amount))
                VerificationModel.create(verif_gold_vals)
                _logger.info("Создана сверка для Золото (положительная)")
                
            except Exception as e:
                _logger.error(f"Ошибка при создании ордера Банк сумм: {e}")
        
        # 3. Банк КБ
        if bank_kb_contragent and bank_kb_payer and self.bank_kb:
            try:
                bank_kb_amount = self.bank_kb
                
                # Создаем ордер
                order_vals = {
                    "date": sale_date,
                    "partner_1_id": gold_contragent.id,
                    "payer_1_id": gold_payer.id,
                    "wallet_1_id": gold_wallet.id,
                    "partner_2_id": bank_kb_contragent.id,
                    "payer_2_id": bank_kb_payer.id,
                    "wallet_2_id": gold_wallet.id,
                    "gold": [(6, 0, [self.id])],
                    "currency": currency,
                    "amount": bank_kb_amount,
                    "type": "transfer",
                    "comment": "Выход золото",
                }
                
                bank_kb_order = OrderModel.create(order_vals)
                _logger.info(f"Создан ордер Банк КБ: {bank_kb_order.name if hasattr(bank_kb_order, 'name') else bank_kb_order.id}")
                
                # Создаем долговой контейнер для Банк КБ
                money_debt_vals = {
                    "date": sale_date,
                    "partner_id": bank_kb_contragent.id,
                    "currency": currency,
                    "amount": -bank_kb_amount,
                    "state": "debt",
                    "wallet_id": gold_wallet.id,
                    "order_id": bank_kb_order.id,
                }
                money_debt_vals.update(self._prepare_currency_fields("USDT", -bank_kb_amount))
                MoneyModel.create(money_debt_vals)
                _logger.info("Создан долговой контейнер для Банк КБ")
                
                # Создаем положительный контейнер для Золото
                money_positive_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "amount": bank_kb_amount,
                    "state": "positive",
                    "wallet_id": gold_wallet.id,
                    "order_id": bank_kb_order.id,
                }
                money_positive_vals.update(self._prepare_currency_fields("USDT", bank_kb_amount))
                MoneyModel.create(money_positive_vals)
                _logger.info("Создан положительный контейнер для Золото (Банк КБ)")
                
                # Создаем сверку для контрагента (отрицательная)
                verif_bank_kb_vals = {
                    "date": sale_date,
                    "partner_id": bank_kb_contragent.id,
                    "currency": currency,
                    "sum": -bank_kb_amount,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "receiver_id": [(6, 0, [bank_kb_payer.id])],
                    "order_id": [(6, 0, [bank_kb_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_bank_kb_vals.update(self._prepare_currency_fields("USDT", -bank_kb_amount))
                VerificationModel.create(verif_bank_kb_vals)
                _logger.info("Создана сверка для Банк КБ (отрицательная)")
                
                # Создаем сверку для Золото (положительная)
                verif_gold_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "sum": bank_kb_amount,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "receiver_id": [(6, 0, [bank_kb_payer.id])],
                    "order_id": [(6, 0, [bank_kb_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_gold_vals.update(self._prepare_currency_fields("USDT", bank_kb_amount))
                VerificationModel.create(verif_gold_vals)
                _logger.info("Создана сверка для Золото (положительная)")
                
            except Exception as e:
                _logger.error(f"Ошибка при создании ордера Банк КБ: {e}")
        
        # 4. Курьер
        if courier_contragent and courier_payer and self.courier:
            try:
                courier_amount = self.courier
                
                # Создаем ордер
                order_vals = {
                    "date": sale_date,
                    "partner_1_id": gold_contragent.id,
                    "payer_1_id": gold_payer.id,
                    "wallet_1_id": gold_wallet.id,
                    "partner_2_id": courier_contragent.id,
                    "payer_2_id": courier_payer.id,
                    "wallet_2_id": gold_wallet.id,
                    "gold": [(6, 0, [self.id])],
                    "currency": currency,
                    "amount": courier_amount,
                    "type": "transfer",
                    "comment": "Выход золото",
                }
                
                courier_order = OrderModel.create(order_vals)
                _logger.info(f"Создан ордер Курьер: {courier_order.name if hasattr(courier_order, 'name') else courier_order.id}")
                
                # Создаем долговой контейнер для Курьера
                money_debt_vals = {
                    "date": sale_date,
                    "partner_id": courier_contragent.id,
                    "currency": currency,
                    "amount": -courier_amount,
                    "state": "debt",
                    "wallet_id": gold_wallet.id,
                    "order_id": courier_order.id,
                }
                money_debt_vals.update(self._prepare_currency_fields("USDT", -courier_amount))
                MoneyModel.create(money_debt_vals)
                _logger.info("Создан долговой контейнер для Курьера")
                
                # Создаем положительный контейнер для Золото
                money_positive_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "amount": courier_amount,
                    "state": "positive",
                    "wallet_id": gold_wallet.id,
                    "order_id": courier_order.id,
                }
                money_positive_vals.update(self._prepare_currency_fields("USDT", courier_amount))
                MoneyModel.create(money_positive_vals)
                _logger.info("Создан положительный контейнер для Золото (Курьер)")
                
                # Создаем сверку для контрагента (отрицательная)
                verif_courier_vals = {
                    "date": sale_date,
                    "partner_id": courier_contragent.id,
                    "currency": currency,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "sum": -courier_amount,
                    "receiver_id": [(6, 0, [courier_payer.id])],
                    "order_id": [(6, 0, [courier_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_courier_vals.update(self._prepare_currency_fields("USDT", -courier_amount))
                VerificationModel.create(verif_courier_vals)
                _logger.info("Создана сверка для Курьера (отрицательная)")
                
                # Создаем сверку для Золото (положительная)
                verif_gold_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "receiver_id": [(6, 0, [courier_payer.id])],
                    "sum": courier_amount,
                    "order_id": [(6, 0, [courier_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_gold_vals.update(self._prepare_currency_fields("USDT", courier_amount))
                VerificationModel.create(verif_gold_vals)
                _logger.info("Создана сверка для Золото (положительная)")
                
            except Exception as e:
                _logger.error(f"Ошибка при создании ордера Курьер: {e}")
        
        _logger.info(f"Скрипт распределения USDT успешно завершён для: {self.name}!")
        return True

    def _action_process_gold_deal_profit_distribution_logic(self):
        self.ensure_one()
        _logger.info(f"Начало обработки 'Распределение прибыли' для сделки: {self.name}")
        self._append_log("[Автоматизация] Проведено распределение прибыли.")
        
        # Поиск необходимых моделей
        ContragentModel = self.env["amanat.contragent"]
        PayerModel = self.env["amanat.payer"]
        WalletModel = self.env["amanat.wallet"]
        OrderModel = self.env["amanat.order"]
        MoneyModel = self.env["amanat.money"]
        VerificationModel = self.env["amanat.reconciliation"]
        
        # Проверка наличия партнеров
        if not self.partner_ids:
            _logger.warning(f"Отсутствуют партнеры для распределения прибыли в сделке: {self.name}")
            return False
        
        # Получаем контрагент "Золото"
        gold_contragent = ContragentModel.search([("name", "=", "Золото")], limit=1)
        if not gold_contragent:
            raise UserError("Не найден контрагент 'Золото'")
        
        # Получаем плательщика "Золото"
        gold_payer = PayerModel.search([("name", "=", "Золото")], limit=1)
        if not gold_payer:
            raise UserError("Не найден плательщик 'Золото'")
        
        # Получаем кошелек "Золото"
        gold_wallet = WalletModel.search([("name", "=", "Золото")], limit=1)
        if not gold_wallet:
            raise UserError("Не найден кошелек 'Золото'")
        
        created_orders = []
        currency = "usdt"  # Валюта для всех операций
        
        # Обрабатываем каждого партнера
        for partner in self.partner_ids:
            # Проверяем наличие необходимых данных
            if not hasattr(partner, 'sale_date') or not partner.sale_date:
                _logger.warning(f"Не указана дата продажи для партнера {partner.name} в сделке {self.name}")
                continue
            
            if not hasattr(partner, 'partner_id') or not partner.partner_id:
                _logger.warning(f"Не указан контрагент для партнера {partner.name} в сделке {self.name}")
                continue
            
            if not hasattr(partner, 'profit') or not partner.profit:
                _logger.warning(f"Не указана прибыль для партнера {partner.name} в сделке {self.name}")
                continue
            
            # Получаем необходимые данные
            sale_date = partner.sale_date
            partner_contragent = partner.partner_id
            profit_amount = partner.profit
            
            # Получаем плательщика для партнера
            partner_payer = None
            if hasattr(partner, 'payer_id') and partner.payer_id:
                partner_payer = partner.payer_id
            else:
                # Ищем плательщика по имени контрагента партнера
                partner_payer = PayerModel.search([("name", "=", partner_contragent.name)], limit=1)
            
            if not partner_payer:
                _logger.warning(f"Не найден плательщик для партнера {partner_contragent.name} в сделке {self.name}")
                continue
            
            _logger.info(f"Обработка партнера {partner_contragent.name}: Дата продажи: {sale_date}, Сумма: {profit_amount} USDT")
            
            try:
                # Создаем ордер "Золото -> Партнер"
                order_vals = {
                    "date": sale_date,
                    "partner_1_id": gold_contragent.id,
                    "payer_1_id": gold_payer.id,
                    "wallet_1_id": gold_wallet.id,
                    "partner_2_id": partner_contragent.id,
                    "payer_2_id": partner_payer.id,
                    "wallet_2_id": gold_wallet.id,
                    "amount": profit_amount,
                    "type": "transfer",
                    "currency": currency,
                    "gold": [(6, 0, [self.id])],  # Связь с текущей сделкой 'Золото'
                    "partner_gold": [(6, 0, [partner.id])],  # Связь с записью 'Партнеры золото'
                    "comment": "Выход золото",
                }
                
                partner_order = OrderModel.create(order_vals)
                created_orders.append(partner_order.id)
                _logger.info(f"Создан ордер для партнера {partner_contragent.name}")
                
                # Создаем долговой контейнер для партнера (с отрицательной суммой)
                money_debt_vals = {
                    "date": sale_date,
                    "partner_id": partner_contragent.id,
                    "currency": currency,
                    "amount": -profit_amount,
                    "state": "debt",
                    "wallet_id": gold_wallet.id,
                    "order_id": partner_order.id,
                }
                money_debt_vals.update(self._prepare_currency_fields("USDT", -profit_amount))
                MoneyModel.create(money_debt_vals)
                _logger.info(f"Создан долговой контейнер для партнера {partner_contragent.name}")
                
                # Создаем положительный контейнер для Золото (с положительной суммой)
                money_positive_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "amount": profit_amount,
                    "state": "positive",
                    "wallet_id": gold_wallet.id,
                    "order_id": partner_order.id,
                }
                money_positive_vals.update(self._prepare_currency_fields("USDT", profit_amount))
                MoneyModel.create(money_positive_vals)
                _logger.info(f"Создан положительный контейнер для Золото на сумму {profit_amount} USDT")
                
                # Создаем сверку для партнера (отрицательная)
                verif_partner_vals = {
                    "date": sale_date,
                    "partner_id": partner_contragent.id,
                    "currency": currency,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "sum": -profit_amount,
                    "receiver_id": [(6, 0, [partner_payer.id])],
                    "order_id": [(6, 0, [partner_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_partner_vals.update(self._prepare_currency_fields("USDT", -profit_amount))
                VerificationModel.create(verif_partner_vals)
                _logger.info(f"Создана сверка для партнера {partner_contragent.name} (отрицательная)")
                
                # Создаем сверку для Золото (положительная)
                verif_gold_vals = {
                    "date": sale_date,
                    "partner_id": gold_contragent.id,
                    "currency": currency,
                    "sender_id": [(6, 0, [gold_payer.id])],
                    "receiver_id": [(6, 0, [partner_payer.id])],
                    "sum": profit_amount,
                    "order_id": [(6, 0, [partner_order.id])],
                    "wallet_id": gold_wallet.id,
                }
                verif_gold_vals.update(self._prepare_currency_fields("USDT", profit_amount))
                VerificationModel.create(verif_gold_vals)
                _logger.info(f"Создана сверка для Золото (положительная)")
                
            except Exception as e:
                _logger.error(f"Ошибка при распределении прибыли для партнера {partner_contragent.name}: {e}")
                continue
        
        # Добавляем созданные ордера к списку ордеров сделки
        if created_orders:
            if self.order_ids:
                self.order_ids = [(4, order_id, 0) for order_id in created_orders]
            else:
                self.order_ids = [(6, 0, created_orders)]
        
        _logger.info(f"Скрипт распределения прибыли успешно завершён для: {self.name}!")
        return True

    # "Золото Вход" Платежка
    @api.onchange('extract_delivery_ids')
    def _onchange_extract_delivery_ids(self):
        for rec in self:
            if rec.extract_delivery_ids:
                _logger.info(f"Изменено поле 'Платежка' для сделки: {rec.name}")
                rec._action_process_gold_deal_payment_logic()
    
    def _action_process_gold_deal_payment_logic(self):
        self.ensure_one()
        _logger.info(f"Начало обработки платежки для сделки: {self.name}")
        self._append_log("[Автоматизация] Проведена обработка платежки.")
        
        # Проверка, что платежка существует
        if not self.extract_delivery_ids:
            _logger.warning(f"Нет привязанной платежки для сделки: {self.name}")
            return False
        
        # Берем первую платежку (в скрипте Airtable также использовалась первая привязанная платежка)
        payment = self.extract_delivery_ids[0]
        bank_gold_payer = self.bank.contragent_id.payer_ids[0]
        
        # Проверка получателя в платежке
        # В скрипте Airtable проверяется, что получатель - контрагент банка
        if not hasattr(payment, 'recipient') or not payment.recipient:
            _logger.warning(f"Не указан получатель в платежке для сделки: {self.name}")
        
        if payment.recipient.name != bank_gold_payer.name:
            _logger.warning(f"Получатель платежки не {bank_gold_payer.name}, завершаем обработку для сделки: {self.name}")
            return False
        
        _logger.info(f"Проверка получателя платежки: {bank_gold_payer.name}, продолжаем обработку")
        
        # Получаем дату из платежки
        if not hasattr(payment, 'date') or not payment.date:
            _logger.warning(f"Не указана дата в платежке для сделки: {self.name}")
            return False
        
        payment_date = payment.date
        payment_amount = payment.amount if hasattr(payment, 'amount') and payment.amount else 0
        
        # Поиск необходимых моделей
        OrderModel = self.env["amanat.order"]
        MoneyModel = self.env["amanat.money"]
        VerificationModel = self.env["amanat.reconciliation"]
        
        # Находим связанные ордера, где Контрагент 2
        # В Odoo можно использовать domain для фильтрации
        domain = [
            ('gold', 'in', [self.id]),  # поле 'gold' содержит ID текущей сделки
        ]
        
        related_orders = OrderModel.search(domain)
        _logger.info(f"Найдено {len(related_orders)} связанных ордеров")
        
        processed_orders = []
        
        # Обрабатываем каждый ордер, где Контрагент 2
        for order in related_orders:
            # Проверяем, что Контрагент 2
            if not order.partner_2_id or order.partner_2_id.name != bank_gold_payer.name:
                _logger.info(f"Пропускаем ордер {order.name} - Контрагент 2 не {bank_gold_payer.name}")
                continue
            
            try:
                _logger.info(f"Обработка ордера с {bank_gold_payer.name} {order.name}:")
                _logger.info(f"- Контрагент 1: {order.partner_1_id.name}")
                _logger.info(f"- Сумма: {payment_amount} RUB")
                
                # Обновляем комментарий ордера
                order.write({"comment": f"Перевод денег на {bank_gold_payer.name} по сделке Золото"})
                
                # Проверяем наличие необходимых данных
                if not order.partner_1_id or not order.wallet_1_id:
                    _logger.warning(f"Пропущен ордер {order.name} - неполные данные")
                    continue
                
                # Создаем долговой контейнер для Контрагента 1
                money_debt_vals = {
                    "date": payment_date,
                    "partner_id": order.partner_1_id.id,
                    "currency": "rub",
                    "amount": -payment_amount,
                    "state": "debt",
                    "wallet_id": order.wallet_1_id.id,
                    "order_id": order.id,
                }
                money_debt_vals.update(self._prepare_currency_fields("RUB", -payment_amount))
                MoneyModel.create(money_debt_vals)
                _logger.info(f"Создан долговой контейнер для {order.partner_1_id.name}")
                
                # Создаем положительный контейнер
                money_positive_vals = {
                    "date": payment_date,
                    "partner_id": order.partner_2_id.id,
                    "currency": "rub",
                    "amount": payment_amount,
                    "state": "positive",
                    "wallet_id": order.wallet_1_id.id,
                    "order_id": order.id,
                }
                money_positive_vals.update(self._prepare_currency_fields("RUB", payment_amount))
                MoneyModel.create(money_positive_vals)
                _logger.info(f"Создан положительный контейнер для {bank_gold_payer.name}")
                
                # Создаем сверку для Контрагента 1 (отрицательная сумма)
                verif_partner1_vals = {
                    "date": payment_date,
                    "partner_id": order.partner_1_id.id,
                    "currency": "rub",
                    "sum": -payment_amount,
                    "sender_id": [(6, 0, [order.payer_1_id.id])] if order.payer_1_id else [(6, 0, [])],
                    "receiver_id": [(6, 0, [order.payer_2_id.id])] if order.payer_2_id else [(6, 0, [])],
                    "order_id": [(6, 0, [order.id])],
                    "wallet_id": order.wallet_1_id.id,
                }
                verif_partner1_vals.update(self._prepare_currency_fields("RUB", -payment_amount))
                VerificationModel.create(verif_partner1_vals)
                _logger.info(f"Создана сверка для {order.partner_1_id.name} с суммой -{payment_amount} RUB")
                
                # Создаем сверку для Контрагента 2 (положительная сумма)
                verif_partner2_vals = {
                    "date": payment_date,
                    "partner_id": order.partner_2_id.id,
                    "currency": "rub",
                    "sum": payment_amount,
                    "sender_id": [(6, 0, [order.payer_1_id.id])] if order.payer_1_id else [(6, 0, [])],
                    "receiver_id": [(6, 0, [order.payer_2_id.id])] if order.payer_2_id else [(6, 0, [])],
                    "order_id": [(6, 0, [order.id])],
                    "wallet_id": order.wallet_1_id.id,
                }
                verif_partner2_vals.update(self._prepare_currency_fields("RUB", payment_amount))
                VerificationModel.create(verif_partner2_vals)
                _logger.info(f"Создана сверка для {order.partner_2_id.name} с суммой +{payment_amount} RUB")
                
                processed_orders.append(order.id)
                
            except Exception as e:
                _logger.error(f"Ошибка при обработке ордера {order.name}: {e}")
        
        if processed_orders:
            _logger.info(f"Успешно обработано {len(processed_orders)} ордеров с {bank_gold_payer.name}")
        else:
            _logger.warning(f"Не найдено ордеров с {bank_gold_payer.name} для обработки или еще не сохранена платежка в золоте")
        
        _logger.info(f"Скрипт обработки платежки успешно завершён для: {self.name}!")
        return True
