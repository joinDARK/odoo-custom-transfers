import logging
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

class ZayavkaSendToReconciliationAutomations(models.Model):
    _inherit = 'amanat.zayavka'

    @api.model
    def run_all_send_to_reconciliation_automations(self):
        if self.is_sberbank_contragent and not self.is_sovcombank_contragent:
            if self.deal_type != "export":
                _logger.info("[ВЫХОД ЗАЯВКИ] Считаем как Сбербанк; Вид сделки: импорт")
                self._run_send_to_reconciliation_sber()
            else:
                _logger.info("[ВЫХОД ЗАЯВКИ] Считаем как Сбербанк; Вид сделки: экспорт")
                self._run_send_to_reconciliation_sber_export()
        elif self.is_sovcombank_contragent and not self.is_sberbank_contragent:
            if self.deal_type != "export":
                _logger.info("[ВЫХОД ЗАЯВКИ] Считаем как Совкомбанк; Вид сделки: импорт")
                self._run_send_to_reconciliation()
            else:
                _logger.info("[ВЫХОД ЗАЯВКИ] Считаем как Совкомбанк; Вид сделки: экспорт")
                self._run_send_to_reconciliation_export()
        else:
            if self.deal_type != "export":
                _logger.info("[ВЫХОД ЗАЯВКИ] Cчитаем как Клиентскую (Индивидуальная); Вид сделки: импорт")
                self._run_send_to_reconciliation_client()
            else:
                _logger.info("[ВЫХОД ЗАЯВКИ] Cчитаем как Клиентскую (Индивидуальная); Вид сделки: экспорт")
                self._run_send_to_reconciliation_client_export()

        self._run_cash_fin_rez_distribution()

    @api.model
    def _run_send_to_reconciliation(self):
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        finka = self.env['amanat.contragent'].search([('name', '=', 'Финка')], limit=1)
        if not finka:
            return

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Получаем/создаём нужные записи
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелёк 'Агентка' не найден.")
            return

        agent = self.agent_id
        if not agent:
            _logger.warning("Поле 'Агент' не заполнено.")
            return

        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("Не найден плательщик агента")
            return
        
        deal_closed_date = self.deal_closed_date
        if not deal_closed_date:
            _logger.warning("Поле 'Сделка закрыта' не заполнено.")
            return

        # Определяем поле для "Скрытая комиссия Партнера" в зависимости от контрагента
        hidden_commission_field = "hidden_partner_commission_real" if contragent.name == "Олег" else "hidden_partner_commission_real_rub"
        hidden_commission_use_rub = False if contragent.name == "Олег" else True

        # Формируем список расходов
        expenses = [
            {
                "contragent2Name": "Платежка РФ",
                "sumField": "payment_order_rf_sovok",
                "useRub": True,
            },
            {
                "contragent2Name": "Себестоимость денег",
                "sumField": "sebestoimost_denej_sovok_real",
                "useRub": False,
            },
            {
                "contragent2Name": "Расход на операционную деятельность",
                "sumField": "operating_expenses_sovok_real_rub",
                "useRub": True,
            },
            {
                "contragent2Name": "Прибыль Плательщика по валюте заявки",
                "sumField": "payer_profit_currency",
                "useRub": False,
            },
            {
                "contragent2Name": "Скрытая комиссия Партнера",
                "sumField": hidden_commission_field,
                "useRub": hidden_commission_use_rub,
            },
            {
                "contragent2Name": "Фин рез",
                "sumField": "fin_res_sovok_real",
                "useRub": False,
            },
        ]

        contragent_model = self.env['amanat.contragent']

        for expense in expenses:
            expenseField = expense["sumField"]
            contragent2Name = expense["contragent2Name"]
            useRub = expense["useRub"]

            contragent2 = contragent_model.search([('name', '=', contragent2Name)], limit=1)
            if not contragent2:
                _logger.warning(f"Контрагент '{contragent2Name}' не найден")
                continue

            sum_value = getattr(self, expenseField, 0)
            if not sum_value or sum_value == 0:
                _logger.warning(f"Сумма в поле '{expenseField}' равна 0, пропускаем расход '{contragent2Name}'")
                continue

            currency = 'rub' if useRub else self.currency

            payer2 = self._get_first_payer(contragent2) if contragent2 else False

            # Создать ордер
            order = self._create_order({
                "date": deal_closed_date,
                "type": "transfer",
                "partner_1_id": agent.id,
                "payer_1_id": agent_payer.id if agent_payer else False,
                "partner_2_id": contragent2.id,
                "payer_2_id": payer2.id if payer2 else False,
                "wallet_1_id": wallet_agentka.id,
                "wallet_2_id": wallet_agentka.id,
                "currency": currency,
                "amount": sum_value,
                "comment": f"расход по заявке № {num_zayavka}",
                "zayavka_ids": [(6, 0, [record_id])],
            })

            # Создать долг (отрицательная сумма)
            self._create_money({
                'date': deal_closed_date,
                'partner_id': contragent2.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': wallet_agentka.id,
                'order_id': order.id,
                **self._get_currency_fields(currency, -sum_value)
            })

            self._create_reconciliation({
                'date': deal_closed_date,
                'currency': currency,
                'order_id': [(4, order.id)],
                'partner_id': contragent2.id,
                'sender_id': [(4, agent_payer.id)],
                'receiver_id': [(4, payer2.id)],
                'wallet_id': wallet_agentka.id,
                **self._get_reconciliation_currency_fields(currency, -sum_value)
            })

        _logger.info("Скрипт завершён: для каждого расхода создан расходной ордер и долговой контейнер")
        return True

    @api.model
    def _run_send_to_reconciliation_sber(self):
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Получаем/создаём нужные записи
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелёк 'Агентка' не найден.")
            return

        agent = self.agent_id
        if not agent:
            _logger.warning("Поле 'Агент' не заполнено.")
            return

        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("Не найден плательщик агента")
            return
        
        deal_closed_date = self.deal_closed_date
        if not deal_closed_date:
            _logger.warning("Поле 'Сделка закрыта' не заполнено.")
            return

        # Определяем поле для "Скрытая комиссия Партнера" в зависимости от контрагента
        hidden_commission_field = "hidden_partner_commission_real" if contragent.name == "Олег" else "hidden_partner_commission_real_rub"
        hidden_commission_use_rub = False if contragent.name == "Олег" else True

        # Формируем список расходов для Сбербанка
        expenses = [
            {
                "contragent2Name": "Платежка РФ",
                "sumField": "payment_order_rf_sber",
                "useRub": True,
            },
            {
                "contragent2Name": "Себестоимость денег",
                "sumField": "sebestoimost_denej_sber_real",
                "useRub": False,
            },
            {
                "contragent2Name": "Расход на операционную деятельность",
                "sumField": "sber_operating_expenses_real_rub",
                "useRub": True,
            },
            {
                "contragent2Name": "Прибыль Плательщика по валюте заявки",
                "sumField": "payer_profit_currency",
                "useRub": False,
            },
            {
                "contragent2Name": "Скрытая комиссия Партнера",
                "sumField": hidden_commission_field,
                "useRub": hidden_commission_use_rub,
            },
            {
                "contragent2Name": "Фин рез",
                "sumField": "fin_res_sber_real",
                "useRub": False,
            },
        ]

        contragent_model = self.env['amanat.contragent']

        for expense in expenses:
            expenseField = expense["sumField"]
            contragent2Name = expense["contragent2Name"]
            useRub = expense["useRub"]

            contragent2 = contragent_model.search([('name', '=', contragent2Name)], limit=1)
            if not contragent2:
                _logger.warning(f"Контрагент '{contragent2Name}' не найден")
                continue

            sum_value = getattr(self, expenseField, 0)
            if not sum_value or sum_value == 0:
                _logger.warning(f"Сумма в поле '{expenseField}' равна 0, пропускаем расход '{contragent2Name}'")
                continue

            currency = 'rub' if useRub else self.currency

            payer2 = self._get_first_payer(contragent2) if contragent2 else False

            # Создать ордер
            order = self._create_order({
                "date": deal_closed_date,
                "type": "transfer",
                "partner_1_id": agent.id,
                "payer_1_id": agent_payer.id if agent_payer else False,
                "partner_2_id": contragent2.id,
                "payer_2_id": payer2.id if payer2 else False,
                "wallet_1_id": wallet_agentka.id,
                "wallet_2_id": wallet_agentka.id,
                "currency": currency,
                "amount": sum_value,
                "comment": f"расход по заявке № {num_zayavka}",
                "zayavka_ids": [(6, 0, [record_id])],
            })

            # Создать долг (отрицательная сумма)
            self._create_money({
                'date': deal_closed_date,
                'partner_id': contragent2.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': wallet_agentka.id,
                'order_id': order.id,
                **self._get_currency_fields(currency, -sum_value)
            })

            self._create_reconciliation({
                'date': deal_closed_date,
                'currency': currency,
                'order_id': [(4, order.id)],
                'partner_id': contragent2.id,
                'sender_id': [(4, agent_payer.id)],
                'receiver_id': [(4, payer2.id)],
                'wallet_id': wallet_agentka.id,
                **self._get_reconciliation_currency_fields(currency, -sum_value)
            })

        _logger.info("Скрипт завершён: для каждого расхода создан расходной ордер и долговой контейнер")
        return True

    @api.model
    def _run_send_to_reconciliation_client(self):
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Поле 'Контрагент' не заполнено.")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Получаем/создаём нужные записи
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелёк 'Агентка' не найден.")
            return

        agent = self.agent_id
        if not agent:
            _logger.warning("Поле 'Агент' не заполнено.")
            return

        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("Не найден плательщик агента")
            return
        
        deal_closed_date = self.deal_closed_date
        if not deal_closed_date:
            _logger.warning("Поле 'Сделка закрыта' не заполнено.")
            return

        # Определяем поле для "Скрытая комиссия Партнера" в зависимости от контрагента
        hidden_commission_field = "hidden_partner_commission_real" if contragent.name == "Олег" else "hidden_partner_commission_real_rub"
        hidden_commission_use_rub = False if contragent.name == "Олег" else True

        # Формируем список расходов для клиентских заявок
        expenses = [
            {
                "contragent2Name": "Платежка РФ",
                "sumField": "payment_order_rf_client",
                "useRub": True,
            },
            {
                "contragent2Name": "Себестоимость денег",
                "sumField": "cost_of_money_client_real",
                "useRub": False,
            },
            {
                "contragent2Name": "Расход на операционную деятельность",
                "sumField": "client_real_operating_expenses_rub",
                "useRub": True,
            },
            {
                "contragent2Name": "Прибыль Плательщика по валюте заявки",
                "sumField": "payer_profit_currency",
                "useRub": False,
            },
            {
                "contragent2Name": "Скрытая комиссия Партнера",
                "sumField": hidden_commission_field,
                "useRub": hidden_commission_use_rub,
            },
            {
                "contragent2Name": "Фин рез",
                "sumField": "fin_res_client_real",
                "useRub": False,
            },
        ]

        contragent_model = self.env['amanat.contragent']

        for expense in expenses:
            expenseField = expense["sumField"]
            contragent2Name = expense["contragent2Name"]
            useRub = expense["useRub"]

            contragent2 = contragent_model.search([('name', '=', contragent2Name)], limit=1)
            if not contragent2:
                _logger.warning(f"Контрагент '{contragent2Name}' не найден")
                continue

            sum_value = getattr(self, expenseField, 0)
            # Проверка на None или 0 (как в Airtable: expenseSum == null || expenseSum === 0)
            if not sum_value or sum_value == 0:
                _logger.warning(f"Поле '{expenseField}' равно 0 или пустое, пропускаем расход '{contragent2Name}'")
                continue

            currency = 'rub' if useRub else self.currency

            payer2 = self._get_first_payer(contragent2) if contragent2 else False

            # Создать ордер
            order = self._create_order({
                "date": deal_closed_date,
                "type": "transfer",
                "partner_1_id": agent.id,
                "payer_1_id": agent_payer.id if agent_payer else False,
                "partner_2_id": contragent2.id,
                "payer_2_id": payer2.id if payer2 else False,
                "wallet_1_id": wallet_agentka.id,
                "wallet_2_id": wallet_agentka.id,
                "currency": currency,
                "amount": sum_value,
                "comment": f"расход по заявке № {num_zayavka}",
                "zayavka_ids": [(6, 0, [record_id])],
            })

            # Создать долг (отрицательная сумма)
            self._create_money({
                'date': deal_closed_date,
                'partner_id': contragent2.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': wallet_agentka.id,
                'order_id': order.id,
                **self._get_currency_fields(currency, -sum_value)
            })

            self._create_reconciliation({
                'date': deal_closed_date,
                'currency': currency,
                'order_id': [(4, order.id)],
                'partner_id': contragent2.id,
                'sender_id': [(4, agent_payer.id)],
                'receiver_id': [(4, payer2.id)],
                'wallet_id': wallet_agentka.id,
                **self._get_reconciliation_currency_fields(currency, -sum_value)
            })

        _logger.info("Скрипт завершён: для каждого расхода (где сумма не равна 0) создан расходной ордер и долговой контейнер")
        return True

    @api.model
    def _run_send_to_reconciliation_export(self):
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Получаем контрагента для определения логики "Скрытая комиссия Партнера"
        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return

        # Получаем/создаём нужные записи
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелёк 'Агентка' не найден.")
            return

        agent = self.agent_id
        if not agent:
            _logger.warning("Поле 'Агент' не заполнено.")
            return

        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("Не найден плательщик агента")
            return
        
        deal_closed_date = self.deal_closed_date
        if not deal_closed_date:
            _logger.warning("Поле 'Сделка закрыта' не заполнено.")
            return

        # Определяем поле для "Скрытая комиссия Партнера" в зависимости от контрагента
        hidden_commission_field = "hidden_partner_commission_real" if contragent.name == "Олег" else "hidden_partner_commission_real_rub"
        hidden_commission_use_rub = False if contragent.name == "Олег" else True

        # Формируем список расходов для экспорта (только 2 элемента)
        expenses = [
            {
                "contragent2Name": "Прибыль Плательщика по валюте заявки",
                "sumField": "payer_profit_currency",
                "useRub": False,
            },
            {
                "contragent2Name": "Скрытая комиссия Партнера",
                "sumField": hidden_commission_field,
                "useRub": hidden_commission_use_rub,
            },
            {
                "contragent2Name": "Фин рез",
                "sumField": "fin_res_sovok_real",
                "useRub": False,
            },
        ]

        contragent_model = self.env['amanat.contragent']

        for expense in expenses:
            expenseField = expense["sumField"]
            contragent2Name = expense["contragent2Name"]
            useRub = expense["useRub"]

            contragent2 = contragent_model.search([('name', '=', contragent2Name)], limit=1)
            if not contragent2:
                _logger.warning(f"Контрагент '{contragent2Name}' не найден")
                continue

            sum_value = getattr(self, expenseField, 0)
            # Проверка на пустое значение или 0 (как в Airtable: !expenseSum || expenseSum === 0)
            if not sum_value or sum_value == 0:
                _logger.warning(f"Поле '{expenseField}' равно 0 или пустое, пропускаем расход '{contragent2Name}'")
                continue

            currency = 'rub' if useRub else self.currency

            payer2 = self._get_first_payer(contragent2) if contragent2 else False

            # Создать ордер
            order = self._create_order({
                "date": deal_closed_date,
                "type": "transfer",
                "partner_1_id": agent.id,
                "payer_1_id": agent_payer.id if agent_payer else False,
                "partner_2_id": contragent2.id,
                "payer_2_id": payer2.id if payer2 else False,
                "wallet_1_id": wallet_agentka.id,
                "wallet_2_id": wallet_agentka.id,
                "currency": currency,
                "amount": sum_value,
                "comment": f"расход по заявке № {num_zayavka}",
                "zayavka_ids": [(6, 0, [record_id])],
            })

            # Создать долг (отрицательная сумма)
            self._create_money({
                'date': deal_closed_date,
                'partner_id': contragent2.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': wallet_agentka.id,
                'order_id': order.id,
                **self._get_currency_fields(currency, -sum_value)
            })

            self._create_reconciliation({
                'date': deal_closed_date,
                'currency': currency,
                'order_id': [(4, order.id)],
                'partner_id': contragent2.id,
                'sender_id': [(4, agent_payer.id)],
                'receiver_id': [(4, payer2.id)],
                'wallet_id': wallet_agentka.id,
                **self._get_reconciliation_currency_fields(currency, -sum_value)
            })

        _logger.info("Скрипт завершён: для каждого расхода (где сумма не равна 0) создан расходной ордер и долговой контейнер")
        return True

    @api.model
    def _run_send_to_reconciliation_sber_export(self):
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Получаем/создаём нужные записи
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелёк 'Агентка' не найден.")
            return

        agent = self.agent_id
        if not agent:
            _logger.warning("Поле 'Агент' не заполнено.")
            return

        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("Не найден плательщик агента")
            return
        
        deal_closed_date = self.deal_closed_date
        if not deal_closed_date:
            _logger.warning("Поле 'Сделка закрыта' не заполнено.")
            return

        # Определяем поле для "Скрытая комиссия Партнера" в зависимости от контрагента
        hidden_commission_field = "hidden_partner_commission_real" if contragent.name == "Олег" else "hidden_partner_commission_real_rub"
        hidden_commission_use_rub = False if contragent.name == "Олег" else True

        # Формируем список расходов для Сбербанка
        expenses = [
            {
                "contragent2Name": "Прибыль Плательщика по валюте заявки",
                "sumField": "payer_profit_currency",
                "useRub": False,
            },
            {
                "contragent2Name": "Скрытая комиссия Партнера",
                "sumField": hidden_commission_field,
                "useRub": hidden_commission_use_rub,
            },
            {
                "contragent2Name": "Фин рез",
                "sumField": "fin_res_sber_real",
                "useRub": False,
            },
        ]

        contragent_model = self.env['amanat.contragent']

        for expense in expenses:
            expenseField = expense["sumField"]
            contragent2Name = expense["contragent2Name"]
            useRub = expense["useRub"]

            contragent2 = contragent_model.search([('name', '=', contragent2Name)], limit=1)
            if not contragent2:
                _logger.warning(f"Контрагент '{contragent2Name}' не найден")
                continue

            sum_value = getattr(self, expenseField, 0)
            if not sum_value or sum_value == 0:
                _logger.warning(f"Сумма в поле '{expenseField}' равна 0, пропускаем расход '{contragent2Name}'")
                continue

            currency = 'rub' if useRub else self.currency

            payer2 = self._get_first_payer(contragent2) if contragent2 else False

            # Создать ордер
            order = self._create_order({
                "date": deal_closed_date,
                "type": "transfer",
                "partner_1_id": agent.id,
                "payer_1_id": agent_payer.id if agent_payer else False,
                "partner_2_id": contragent2.id,
                "payer_2_id": payer2.id if payer2 else False,
                "wallet_1_id": wallet_agentka.id,
                "wallet_2_id": wallet_agentka.id,
                "currency": currency,
                "amount": sum_value,
                "comment": f"расход по заявке № {num_zayavka}",
                "zayavka_ids": [(6, 0, [record_id])],
            })

            # Создать долг (отрицательная сумма)
            self._create_money({
                'date': deal_closed_date,
                'partner_id': contragent2.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': wallet_agentka.id,
                'order_id': order.id,
                **self._get_currency_fields(currency, -sum_value)
            })

            self._create_reconciliation({
                'date': deal_closed_date,
                'currency': currency,
                'order_id': [(4, order.id)],
                'partner_id': contragent2.id,
                'sender_id': [(4, agent_payer.id)],
                'receiver_id': [(4, payer2.id)],
                'wallet_id': wallet_agentka.id,
                **self._get_reconciliation_currency_fields(currency, -sum_value)
            })

        _logger.info("Скрипт завершён: для каждого расхода создан расходной ордер и долговой контейнер")
        return True

    @api.model
    def _run_send_to_reconciliation_client_export(self):
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Поле 'Контрагент' не заполнено.")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Получаем/создаём нужные записи
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелёк 'Агентка' не найден.")
            return

        agent = self.agent_id
        if not agent:
            _logger.warning("Поле 'Агент' не заполнено.")
            return

        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("Не найден плательщик агента")
            return
        
        deal_closed_date = self.deal_closed_date
        if not deal_closed_date:
            _logger.warning("Поле 'Сделка закрыта' не заполнено.")
            return

        # Определяем поле для "Скрытая комиссия Партнера" в зависимости от контрагента
        hidden_commission_field = "hidden_partner_commission_real" if contragent.name == "Олег" else "hidden_partner_commission_real_rub"
        hidden_commission_use_rub = False if contragent.name == "Олег" else True

        # Формируем список расходов для клиентских заявок
        expenses = [
            {
                "contragent2Name": "Прибыль Плательщика по валюте заявки",
                "sumField": "payer_profit_currency",
                "useRub": False,
            },
            {
                "contragent2Name": "Скрытая комиссия Партнера",
                "sumField": hidden_commission_field,
                "useRub": hidden_commission_use_rub,
            },
            {
                "contragent2Name": "Фин рез",
                "sumField": "fin_res_client_real",
                "useRub": False,
            },
        ]

        contragent_model = self.env['amanat.contragent']

        for expense in expenses:
            expenseField = expense["sumField"]
            contragent2Name = expense["contragent2Name"]
            useRub = expense["useRub"]

            contragent2 = contragent_model.search([('name', '=', contragent2Name)], limit=1)
            if not contragent2:
                _logger.warning(f"Контрагент '{contragent2Name}' не найден")
                continue

            sum_value = getattr(self, expenseField, 0)
            # Проверка на None или 0 (как в Airtable: expenseSum == null || expenseSum === 0)
            if not sum_value or sum_value == 0:
                _logger.warning(f"Поле '{expenseField}' равно 0 или пустое, пропускаем расход '{contragent2Name}'")
                continue

            currency = 'rub' if useRub else self.currency

            payer2 = self._get_first_payer(contragent2) if contragent2 else False

            # Создать ордер
            order = self._create_order({
                "date": deal_closed_date,
                "type": "transfer",
                "partner_1_id": agent.id,
                "payer_1_id": agent_payer.id if agent_payer else False,
                "partner_2_id": contragent2.id,
                "payer_2_id": payer2.id if payer2 else False,
                "wallet_1_id": wallet_agentka.id,
                "wallet_2_id": wallet_agentka.id,
                "currency": currency,
                "amount": sum_value,
                "comment": f"расход по заявке № {num_zayavka}",
                "zayavka_ids": [(6, 0, [record_id])],
            })

            # Создать долг (отрицательная сумма)
            self._create_money({
                'date': deal_closed_date,
                'partner_id': contragent2.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': wallet_agentka.id,
                'order_id': order.id,
                **self._get_currency_fields(currency, -sum_value)
            })

            self._create_reconciliation({
                'date': deal_closed_date,
                'currency': currency,
                'order_id': [(4, order.id)],
                'partner_id': contragent2.id,
                'sender_id': [(4, agent_payer.id)],
                'receiver_id': [(4, payer2.id)],
                'wallet_id': wallet_agentka.id,
                **self._get_reconciliation_currency_fields(currency, -sum_value)
            })

        _logger.info("Скрипт завершён: для каждого расхода (где сумма не равна 0) создан расходной ордер и долговой контейнер")
        return True

    @api.model
    def _run_cash_fin_rez_distribution(self):
        """
        Распределение финреза по кассам.
        Создаёт положительный контейнер для "Фин рез" и долговой для соответствующей кассы.
        """
        _logger.info("Скрипт запущен: Распределение финреза по кассам (_run_cash_fin_rez_distribution)")
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        # Получаем контрагента из заявки
        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Поле 'Контрагент' не заполнено в заявке.")
            return
        
        _logger.info(f"Контрагент из заявки: {contragent.name}")

        # Получаем модели касс
        kassa_ivan_model = self.env['amanat.kassa_ivan']
        kassa_3_model = self.env['amanat.kassa_3']
        kassa_2_model = self.env['amanat.kassa_2']
        
        # Ищем участника в кассах с приоритетом: Касса Иван → Касса 3 → Касса 2
        cash_record = None
        cash_source = None
        
        # Поиск в Касса Иван
        cash_record = kassa_ivan_model.search([('contragent_id', '=', contragent.id)], limit=1)
        if cash_record:
            cash_source = "Касса Иван"
            _logger.info(f"Участник '{contragent.name}' найден в таблице 'Касса Иван' (ID={cash_record.id})")
        
        # Если не найден, ищем в Касса 3
        if not cash_record:
            cash_record = kassa_3_model.search([('contragent_id', '=', contragent.id)], limit=1)
            if cash_record:
                cash_source = "Касса 3"
                _logger.info(f"Участник '{contragent.name}' найден в таблице 'Касса 3' (ID={cash_record.id})")
        
        # Если не найден, ищем в Касса 2
        if not cash_record:
            cash_record = kassa_2_model.search([('contragent_id', '=', contragent.id)], limit=1)
            if cash_record:
                cash_source = "Касса 2"
                _logger.info(f"Участник '{contragent.name}' найден в таблице 'Касса 2' (ID={cash_record.id})")
        
        if not cash_record:
            _logger.warning(f"Участник '{contragent.name}' не найден ни в одной из касс")
            return

        # Определяем поле финреза в зависимости от контрагента
        if contragent.name == "Совкомбанк":
            fin_rez_field = "fin_res_sovok_real"
        elif contragent.name == "Cбербанк":
            fin_rez_field = "fin_res_sber_real"
        else:
            fin_rez_field = "fin_res_client_real"
        
        fin_rez_sum = getattr(self, fin_rez_field, 0)
        if not fin_rez_sum or fin_rez_sum == 0:
            _logger.warning(f"Поле '{fin_rez_field}' равно 0 или пустое, операция не выполняется.")
            return
        
        _logger.info(f"Сумма финреза ({fin_rez_field}): {fin_rez_sum}")

        # Получаем процент из найденной записи кассы
        percent = cash_record.percent
        if percent == 0:
            _logger.warning(f"Процент для кассы '{cash_source}' равен 0, операция не выполняется.")
            return

        # Умножаем на процент
        used_fin_rez_sum = fin_rez_sum * percent
        _logger.info(f"Используемая сумма финреза для контейнеров: {used_fin_rez_sum} (процент кассы: {percent})")

        # Определяем валюту и дату
        currency = self.currency or 'rub'
        deal_closed_date = self.deal_closed_date or fields.Date.today()
        _logger.info(f"Валюта: {currency}, Дата сделки: {deal_closed_date}")

        # Находим контрагента "Фин рез"
        contragent_model = self.env['amanat.contragent']
        fin_rez_contragent = contragent_model.search([('name', '=', 'Фин рез')], limit=1)
        if not fin_rez_contragent:
            _logger.warning("Контрагент 'Фин рез' не найден в таблице 'Контрагент'.")
            return
        
        _logger.info(f"Найден контрагент 'Фин рез' (ID={fin_rez_contragent.id})")

        # Ищем ордера с контрагентом "Фин рез" для данной заявки
        order_model = self.env['amanat.order']
        fin_rez_orders = order_model.search([
            ('zayavka_ids', 'in', record_id),
            '|',
            ('partner_1_id', '=', fin_rez_contragent.id),
            ('partner_2_id', '=', fin_rez_contragent.id)
        ])
        
        if not fin_rez_orders:
            _logger.warning(f"Не найдены ордера с контрагентом 'Фин рез' для заявки {record_id}")
        
        _logger.info(f"Найдено {len(fin_rez_orders)} ордеров с контрагентом 'Фин рез'")
        
        # Берем первый найденный ордер
        fin_rez_order = fin_rez_orders[0]
        _logger.info(f"Используем ордер ID={fin_rez_order.id} для привязки контейнеров")

        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелёк 'Агентка' не найден.")
        
        # Находим держателя для долгового контейнера
        cash_holder = contragent_model.search([('name', '=', cash_source)], limit=1)
        if not cash_holder:
            _logger.warning(f"Запись для держателя с наименованием '{cash_source}' не найдена в таблице 'Контрагент'.")
            return
        
        _logger.info(f"Найден держатель '{cash_holder.name}' (ID={cash_holder.id})")

        # Создаём положительный контейнер для финреза
        positive_container = self._create_money({
            'date': deal_closed_date,
            'partner_id': fin_rez_contragent.id,
            'currency': currency,
            'state': 'positive',
            'wallet_id': wallet_agentka.id if wallet_agentka else False,  # Кошелёк не указан в скрипте
            'order_id': fin_rez_order.id if fin_rez_order else False,  # Привязываем к найденному ордеру
            **self._get_currency_fields(currency, used_fin_rez_sum)
        })
        _logger.info(f"Создан положительный контейнер для 'Фин рез' (ID={positive_container.id}), сумма: {used_fin_rez_sum} {currency} {fin_rez_order}")

        # Создаем сверку
        self._create_reconciliation({
            'date': deal_closed_date,
            'partner_id': fin_rez_contragent.id,
            'currency': currency,
            'order_id': [(4, fin_rez_order.id)],
            'sender_id': [(4, fin_rez_contragent.payer_ids[0].id)],
            'receiver_id': [(4, cash_holder.payer_ids[0].id)],
            'wallet_id': wallet_agentka.id if wallet_agentka else False,
            **self._get_reconciliation_currency_fields(currency, used_fin_rez_sum)
        })
        _logger.info(f"Создана сверка для 'Фин рез', сумма: {used_fin_rez_sum} {currency} {fin_rez_contragent.name} {cash_holder.name}")

        # Создаём долговой контейнер
        debt_container = self._create_money({
            'date': deal_closed_date,
            'partner_id': cash_holder.id,
            'currency': currency,
            'state': 'debt',
            'wallet_id': wallet_agentka.id if wallet_agentka else False,  # Кошелёк не указан в скрипте
            'order_id': fin_rez_order.id if fin_rez_order else False,  # Привязываем к тому же ордеру
            **self._get_currency_fields(currency, -used_fin_rez_sum)
        })
        _logger.info(f"Создан долговой контейнер для '{cash_source}' (Держатель: {cash_holder.name}, ID={debt_container.id}), сумма: -{used_fin_rez_sum} {currency} {fin_rez_order}")

        # Создаем сверку
        self._create_reconciliation({
            'date': deal_closed_date,
            'partner_id': cash_holder.id,
            'currency': currency,
            'order_id': [(4, fin_rez_order.id)],
            'sender_id': [(4, fin_rez_contragent.payer_ids[0].id)],
            'receiver_id': [(4, cash_holder.payer_ids[0].id)],
            'wallet_id': wallet_agentka.id if wallet_agentka else False,
            **self._get_reconciliation_currency_fields(currency, -used_fin_rez_sum)
        })
        _logger.info(f"Создана сверка для '{cash_source}', сумма: -{used_fin_rez_sum} {currency} {cash_holder.name} {fin_rez_contragent.name}")

        _logger.info("Скрипт завершён: создан положительный контейнер для Фин рез и долговой контейнер для выбранной кассы.")
        return True
    