import logging
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

class ZayavkaFixCourseAutomations(models.Model):
    _inherit = 'amanat.zayavka'

    @api.model
    def run_all_fix_course_automations(self):
        self._run_fix_course_sovok_import()
        self._run_fix_course_sber_import()
        self._run_fix_course_client_import()
        self._run_fix_course_sovok_export()
        self._run_fix_course_sber_export()
        self._run_fix_course_client_export()

    @api.model
    def _run_fix_course_sovok_import(self):
        """
        Создание ордеров и контейнеров при фиксации курса для Совкомбанка (Импорт).
        Order 1: Клиент → Агент (RUB)
        Order 2: Агент → Субагент (валюта заявки)
        """
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        # Проверка контрагента - должен быть Совкомбанк
        contragent = self.contragent_id
        if not contragent or contragent.name != "Совкомбанк":
            _logger.warning(f"Контрагент не равен 'Совкомбанк' (найден: '{contragent.name if contragent else 'Не указан'}'). Скрипт остановлен.")
            return

        # Проверка вида сделки - должен быть Импорт
        if self.deal_type != "import":
            _logger.warning(f"Вид сделки не равен 'Импорт' (найден: '{self.deal_type}'). Скрипт остановлен.")
            return

        # Извлекаем необходимые поля
        total_sovok = self.total_sovok
        order_amount = self.amount
        
        if total_sovok is None or order_amount is None:
            _logger.warning("Не заполнены суммы 'Итого Совок' или 'Сумма заявки'.")
            return

        agent = self.agent_id
        subagent = self.subagent_ids[0] if self.subagent_ids else None
        client = self.client_id
        
        if not agent or not subagent or not client:
            _logger.warning("Поля 'Агент', 'Субагент' или 'Клиент' не заполнены.")
            return

        currency = self.currency
        if not currency:
            _logger.warning("Поле 'Валюта' не заполнено.")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Плательщик субагента
        subagent_payer = self.subagent_payer_ids[0] if self.subagent_payer_ids else None
        if not subagent_payer:
            _logger.warning("Поле 'Плательщик Субагента' не заполнено.")
            return

        # Дата - сегодня
        date = fields.Date.today()
        _logger.info(f"Установлена дата: {date}")

        # Получаем плательщиков
        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        
        if not client_payer:
            _logger.warning("Не найден плательщик для Клиента.")
            return
        if not agent_payer:
            _logger.warning("Не найден плательщик для Агента.")
            return

        # Получаем кошелек "Агентка"
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        # Создаем Order 1: Клиент → Агент, сумма = "Итого Совок", валюта = RUB
        order1 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': client.id,
            'payer_1_id': client_payer.id,
            'partner_2_id': agent.id,
            'payer_2_id': agent_payer.id,
            'amount': total_sovok,
            'currency': 'rub',  # Принудительно RUB
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 1 (Клиент → Агент, RUB) создан, ID: {order1.id}")

        # Создаем Order 2: Агент → Субагент, сумма = "Сумма заявки", валюта из заявки
        order2 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': agent.id,
            'payer_1_id': agent_payer.id,
            'partner_2_id': subagent.id,
            'payer_2_id': subagent_payer.id,
            'amount': order_amount,
            'currency': currency,
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 2 (Агент → Субагент) создан, ID: {order2.id}")

        # Создаем контейнер для Order 1 - Положительный для Клиента в RUB
        self._create_money({
            'date': date,
            'partner_id': client.id,
            'currency': 'rub',
            'state': 'positive',
            'wallet_id': wallet_agentka.id,
            'order_id': order1.id,
            **self._get_currency_fields('rub', total_sovok)
        })
        _logger.info("Контейнер для Order 1 (на Клиент, Положительный) создан")

        # Создаем контейнер для Order 2 - Долговой для Субагента в валюте заявки
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt',
            'wallet_id': wallet_agentka.id,
            'order_id': order2.id,
            **self._get_currency_fields(currency, -order_amount)
        })
        _logger.info("Контейнер для Order 2 (на Субагент, Долг) создан")

        _logger.info("Скрипт завершён успешно.")
        return True

    @api.model
    def _run_fix_course_sber_import(self):
        """
        Создание ордеров и контейнеров при фиксации курса для Сбербанка (Импорт).
        Order 1: Клиент → Агент (RUB)
        Order 2: Агент → Субагент (валюта заявки)
        """
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        # Проверка контрагента - должен быть Сбербанк
        contragent = self.contragent_id
        if not contragent or contragent.name != "Cбербанк":
            _logger.warning(f"Контрагент не равен 'Сбербанк' (найден: '{contragent.name if contragent else 'Не указан'}'). Скрипт остановлен.")
            return

        # Проверка вида сделки - должен быть Импорт
        if self.deal_type != "import":
            _logger.warning(f"Вид сделки не равен 'Импорт' (найден: '{self.deal_type}'). Скрипт остановлен.")
            return

        # Извлекаем необходимые поля
        total_sber = self.total_sber
        order_amount = self.amount
        
        if total_sber is None or order_amount is None:
            _logger.warning("Не заполнены суммы 'Итого Сбер' или 'Сумма заявки'.")
            return

        agent = self.agent_id
        subagent = self.subagent_ids[0] if self.subagent_ids else None
        client = self.client_id
        
        if not agent or not subagent or not client:
            _logger.warning("Поля 'Агент', 'Субагент' или 'Клиент' не заполнены.")
            return

        currency = self.currency
        if not currency:
            _logger.warning("Поле 'Валюта' не заполнено.")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Плательщик субагента
        subagent_payer = self.subagent_payer_ids[0] if self.subagent_payer_ids else None
        if not subagent_payer:
            _logger.warning("Поле 'Плательщик Субагента' не заполнено.")
            return

        # Дата - сегодня
        date = fields.Date.today()
        _logger.info(f"Установлена дата: {date}")

        # Получаем плательщиков
        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        
        if not client_payer:
            _logger.warning("Не найден плательщик для Клиента.")
            return
        if not agent_payer:
            _logger.warning("Не найден плательщик для Агента.")
            return

        # Получаем кошелек "Агентка"
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        # Создаем Order 1: Клиент → Агент, сумма = "Итого Сбер", валюта = RUB
        order1 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': client.id,
            'payer_1_id': client_payer.id,
            'partner_2_id': agent.id,
            'payer_2_id': agent_payer.id,
            'amount': total_sber,
            'currency': 'rub',  # Принудительно RUB
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 1 (Клиент → Агент, RUB) создан, ID: {order1.id}")

        # Создаем Order 2: Агент → Субагент, сумма = "Сумма заявки", валюта из заявки
        order2 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': agent.id,
            'payer_1_id': agent_payer.id,
            'partner_2_id': subagent.id,
            'payer_2_id': subagent_payer.id,
            'amount': order_amount,
            'currency': currency,
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 2 (Агент → Субагент) создан, ID: {order2.id}")

        # Создаем контейнер для Order 1 - Положительный для Клиента в RUB
        self._create_money({
            'date': date,
            'partner_id': client.id,
            'currency': 'rub',
            'state': 'positive',
            'wallet_id': wallet_agentka.id,
            'order_id': order1.id,
            **self._get_currency_fields('rub', total_sber)
        })
        _logger.info("Контейнер для Order 1 (на Клиент, Положительный) создан")

        # Создаем контейнер для Order 2 - Долговой для Субагента в валюте заявки
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt',
            'wallet_id': wallet_agentka.id,
            'order_id': order2.id,
            **self._get_currency_fields(currency, -order_amount)
        })
        _logger.info("Контейнер для Order 2 (на Субагент, Долг) создан")

        _logger.info("Скрипт завершён успешно.")
        return True
    
    @api.model
    def _run_fix_course_client_import(self):
        """
        Создание ордеров и контейнеров при фиксации курса для клиентских заявок (Импорт).
        Для контрагентов, которые не являются ни Совкомбанком, ни Сбербанком.
        Order 1: Клиент → Агент (RUB)
        Order 2: Агент → Субагент (валюта заявки)
        """
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        # Проверка контрагента - НЕ должен быть Совкомбанк или Сбербанк
        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Поле 'Контрагент' не заполнено.")
            return
            
        if contragent.name == "Совкомбанк" or contragent.name == "Cбербанк":
            _logger.warning(f"Контрагент равен '{contragent.name}'. Скрипт остановлен.")
            return

        # Проверка вида сделки - должен быть Импорт
        if self.deal_type != "import":
            _logger.warning(f"Вид сделки не равен 'Импорт' (найден: '{self.deal_type}'). Скрипт остановлен.")
            return

        # Извлекаем необходимые поля
        total_client = self.total_client
        order_amount = self.amount
        
        if total_client is None or order_amount is None:
            _logger.warning("Не заполнены суммы 'Итого Клиент' или 'Сумма заявки'.")
            return

        agent = self.agent_id
        subagent = self.subagent_ids[0] if self.subagent_ids else None
        client = self.client_id
        
        if not agent or not subagent or not client:
            _logger.warning("Поля 'Агент', 'Субагент' или 'Клиент' не заполнены.")
            return

        currency = self.currency
        if not currency:
            _logger.warning("Поле 'Валюта' не заполнено.")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Плательщик субагента
        subagent_payer = self.subagent_payer_ids[0] if self.subagent_payer_ids else None
        if not subagent_payer:
            _logger.warning("Поле 'Плательщик Субагента' не заполнено.")
            return

        # Дата - сегодня
        date = fields.Date.today()
        _logger.info(f"Установлена дата: {date}")

        # Получаем плательщиков
        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        
        if not client_payer:
            _logger.warning("Не найден плательщик для Клиента.")
            return
        if not agent_payer:
            _logger.warning("Не найден плательщик для Агента.")
            return

        # Получаем кошелек "Агентка"
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        # Создаем Order 1: Клиент → Агент, сумма = "Итого Клиент", валюта = RUB
        order1 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': client.id,
            'payer_1_id': client_payer.id,
            'partner_2_id': agent.id,
            'payer_2_id': agent_payer.id,
            'amount': total_client,
            'currency': 'rub',  # Принудительно RUB
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 1 (Клиент → Агент, RUB) создан, ID: {order1.id}")

        # Создаем Order 2: Агент → Субагент, сумма = "Сумма заявки", валюта из заявки
        order2 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': agent.id,
            'payer_1_id': agent_payer.id,
            'partner_2_id': subagent.id,
            'payer_2_id': subagent_payer.id,
            'amount': order_amount,
            'currency': currency,
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 2 (Агент → Субагент) создан, ID: {order2.id}")

        # Создаем контейнер для Order 1 - Положительный для Клиента в RUB
        self._create_money({
            'date': date,
            'partner_id': client.id,
            'currency': 'rub',
            'state': 'positive',
            'wallet_id': wallet_agentka.id,
            'order_id': order1.id,
            **self._get_currency_fields('rub', total_client)
        })
        _logger.info("Контейнер для Order 1 (на Клиент, Положительный) создан")

        # Создаем контейнер для Order 2 - Долговой для Субагента в валюте заявки
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt',
            'wallet_id': wallet_agentka.id,
            'order_id': order2.id,
            **self._get_currency_fields(currency, -order_amount)
        })
        _logger.info("Контейнер для Order 2 (на Субагент, Долг) создан")

        _logger.info("Скрипт завершён успешно.")
        return True
    
    @api.model
    def _run_fix_course_sovok_export(self):
        """
        Создание ордеров и контейнеров при фиксации курса для Совкомбанка (Экспорт).
        Обмен ролей:
        Order 1: Агент → Клиент (RUB) 
        Order 2: Субагент → Агент (валюта заявки)
        """
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        # Проверка контрагента - должен быть Совкомбанк
        contragent = self.contragent_id
        if not contragent or contragent.name != "Совкомбанк":
            _logger.warning(f"Контрагент не равен 'Совкомбанк' (найден: '{contragent.name if contragent else 'Не указан'}'). Скрипт остановлен.")
            return

        # Проверка вида сделки - должен быть Экспорт
        if self.deal_type != "export":
            _logger.warning(f"Вид сделки не равен 'Экспорт' (найден: '{self.deal_type}'). Скрипт остановлен.")
            return

        # Извлекаем необходимые поля
        total_sovok = self.total_sovok  # Используем "Итого Совок" для Order 1
        order_amount = self.amount
        
        if total_sovok is None or order_amount is None:
            _logger.warning("Не заполнены суммы 'Итого Совок' или 'Сумма заявки'.")
            return

        agent = self.agent_id
        subagent = self.subagent_ids[0] if self.subagent_ids else None
        client = self.client_id
        
        if not agent or not subagent or not client:
            _logger.warning("Поля 'Агент', 'Субагент' или 'Клиент' не заполнены.")
            return

        currency = self.currency
        if not currency:
            _logger.warning("Поле 'Валюта' не заполнено.")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Плательщик субагента
        subagent_payer = self.subagent_payer_ids[0] if self.subagent_payer_ids else None
        if not subagent_payer:
            _logger.warning("Поле 'Плательщик Субагента' не заполнено.")
            return

        # Дата - сегодня
        date = fields.Date.today()
        _logger.info(f"Установлена дата: {date}")

        # Получаем плательщиков
        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        
        if not client_payer:
            _logger.warning("Не найден плательщик для Клиента.")
            return
        if not agent_payer:
            _logger.warning("Не найден плательщик для Агента.")
            return

        # Получаем кошелек "Агентка"
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        # Создаем Order 1: Агент → Клиент, сумма = "Итого Совок", валюта = RUB
        order1 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': agent.id,      # Агент отправляет
            'payer_1_id': agent_payer.id,
            'partner_2_id': client.id,      # Клиент получает
            'payer_2_id': client_payer.id,
            'amount': total_sovok,
            'currency': 'rub',  # Принудительно RUB
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 1 (Агент → Клиент, RUB) создан, ID: {order1.id}")

        # Создаем Order 2: Субагент → Агент, сумма = "Сумма заявки", валюта из заявки
        order2 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id,    # Субагент отправляет
            'payer_1_id': subagent_payer.id,
            'partner_2_id': agent.id,       # Агент получает
            'payer_2_id': agent_payer.id,
            'amount': order_amount,
            'currency': currency,
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 2 (Субагент → Агент) создан, ID: {order2.id}")

        # Создаем контейнер для Order 1 - Долговой для Клиента в RUB
        self._create_money({
            'date': date,
            'partner_id': client.id,
            'currency': 'rub',
            'state': 'debt',
            'wallet_id': wallet_agentka.id,
            'order_id': order1.id,
            **self._get_currency_fields('rub', -total_sovok)
        })
        _logger.info("Контейнер для Order 1 (на Клиент, Долг) создан")

        # Создаем контейнер для Order 2 - Положительный для Субагента в валюте заявки
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'positive',
            'wallet_id': wallet_agentka.id,
            'order_id': order2.id,
            **self._get_currency_fields(currency, order_amount)
        })
        _logger.info("Контейнер для Order 2 (на Субагент, Положительный) создан")

        _logger.info("Скрипт завершён успешно.")
        return True
    
    @api.model
    def _run_fix_course_sber_export(self):
        """
        Создание ордеров и контейнеров при фиксации курса для Сбербанка (Экспорт).
        Обмен ролей:
        Order 1: Агент → Клиент (RUB)
        Order 2: Субагент → Агент (валюта заявки)
        """
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        # Проверка контрагента - должен быть Сбербанк
        contragent = self.contragent_id
        if not contragent or contragent.name != "Сбербанк":
            _logger.warning(f"Контрагент не равен 'Сбербанк' (найден: '{contragent.name if contragent else 'Не указан'}'). Скрипт остановлен.")
            return

        # Проверка вида сделки - должен быть Экспорт
        if self.deal_type != "export":
            _logger.warning(f"Вид сделки не равен 'Экспорт' (найден: '{self.deal_type}'). Скрипт остановлен.")
            return

        # Извлекаем необходимые поля
        total_sber = self.total_sber  # Используем "Итого Сбер" для Order 1
        order_amount = self.amount
        
        if total_sber is None or order_amount is None:
            _logger.warning("Не заполнены суммы 'Итого Сбер' или 'Сумма заявки'.")
            return

        agent = self.agent_id
        subagent = self.subagent_ids[0] if self.subagent_ids else None
        client = self.client_id
        
        if not agent or not subagent or not client:
            _logger.warning("Поля 'Агент', 'Субагент' или 'Клиент' не заполнены.")
            return

        currency = self.currency
        if not currency:
            _logger.warning("Поле 'Валюта' не заполнено.")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Плательщик субагента
        subagent_payer = self.subagent_payer_ids[0] if self.subagent_payer_ids else None
        if not subagent_payer:
            _logger.warning("Поле 'Плательщик Субагента' не заполнено.")
            return

        # Дата - сегодня
        date = fields.Date.today()
        _logger.info(f"Установлена дата: {date}")

        # Получаем плательщиков
        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        
        if not client_payer:
            _logger.warning("Не найден плательщик для Клиента.")
            return
        if not agent_payer:
            _logger.warning("Не найден плательщик для Агента.")
            return

        # Получаем кошелек "Агентка"
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        # Создаем Order 1: Агент → Клиент, сумма = "Итого Сбер", валюта = RUB
        order1 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': agent.id,      # Агент отправляет
            'payer_1_id': agent_payer.id,
            'partner_2_id': client.id,      # Клиент получает
            'payer_2_id': client_payer.id,
            'amount': total_sber,
            'currency': 'rub',  # Принудительно RUB
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 1 (Агент → Клиент, RUB) создан, ID: {order1.id}")

        # Создаем Order 2: Субагент → Агент, сумма = "Сумма заявки", валюта из заявки
        order2 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id,    # Субагент отправляет
            'payer_1_id': subagent_payer.id,
            'partner_2_id': agent.id,       # Агент получает
            'payer_2_id': agent_payer.id,
            'amount': order_amount,
            'currency': currency,
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 2 (Субагент → Агент) создан, ID: {order2.id}")

        # Создаем контейнер для Order 1 - Долговой для Клиента в RUB
        self._create_money({
            'date': date,
            'partner_id': client.id,
            'currency': 'rub',
            'state': 'debt',
            'wallet_id': wallet_agentka.id,
            'order_id': order1.id,
            **self._get_currency_fields('rub', -total_sber)
        })
        _logger.info("Контейнер для Order 1 (на Клиент, Долг) создан")

        # Создаем контейнер для Order 2 - Положительный для Субагента в валюте заявки
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'positive',
            'wallet_id': wallet_agentka.id,
            'order_id': order2.id,
            **self._get_currency_fields(currency, order_amount)
        })
        _logger.info("Контейнер для Order 2 (на Субагент, Положительный) создан")

        _logger.info("Скрипт завершён успешно.")
        return True
    
    @api.model
    def _run_fix_course_client_export(self):
        """
        Создание ордеров и контейнеров при фиксации курса для клиентских заявок (Экспорт).
        Для контрагентов, которые не являются ни Совкомбанком, ни Сбербанком.
        Order 1: Агент → Клиент (RUB)
        Order 2: Субагент → Агент (валюта заявки)
        """
        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        # Проверка контрагента - НЕ должен быть Совкомбанк или Сбербанк
        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Поле 'Контрагент' не заполнено.")
            return
            
        if contragent.name in ("Совкомбанк", "Сбербанк"):
            _logger.warning(f"Контрагент равен '{contragent.name}'. Скрипт остановлен.")
            return

        # Проверка вида сделки - должен быть Экспорт
        if self.deal_type != "export":
            _logger.warning(f"Вид сделки не равен 'Экспорт' (найден: '{self.deal_type}'). Скрипт остановлен.")
            return

        # Извлекаем необходимые поля
        total_client = self.total_client
        order_amount = self.amount
        
        if total_client is None or order_amount is None:
            _logger.warning("Не заполнены суммы 'Итого Клиент' или 'Сумма заявки'.")
            return

        agent = self.agent_id
        subagent = self.subagent_ids[0] if self.subagent_ids else None
        client = self.client_id
        
        if not agent or not subagent or not client:
            _logger.warning("Поля 'Агент', 'Субагент' или 'Клиент' не заполнены.")
            return

        currency = self.currency
        if not currency:
            _logger.warning("Поле 'Валюта' не заполнено.")
            return

        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Поле '№ заявки' не заполнено.")
            return

        # Плательщик субагента
        subagent_payer = self.subagent_payer_ids[0] if self.subagent_payer_ids else None
        if not subagent_payer:
            _logger.warning("Поле 'Плательщик Субагента' не заполнено.")
            return

        # Дата - сегодня
        date = fields.Date.today()
        _logger.info(f"Установлена дата: {date}")

        # Получаем плательщиков
        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        
        if not client_payer:
            _logger.warning("Не найден плательщик для Клиента.")
            return
        if not agent_payer:
            _logger.warning("Не найден плательщик для Агента.")
            return

        # Получаем кошелек "Агентка"
        wallet_agentka = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet_agentka:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        # Создаем Order 1: Агент → Клиент, сумма = "Итого Клиент", валюта = RUB
        order1 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': agent.id,      # Агент отправляет
            'payer_1_id': agent_payer.id,
            'partner_2_id': client.id,      # Клиент получает
            'payer_2_id': client_payer.id,
            'amount': total_client,
            'currency': 'rub',  # Принудительно RUB
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 1 (Агент → Клиент, RUB) создан, ID: {order1.id}")

        # Создаем Order 2: Субагент → Агент, сумма = "Сумма заявки", валюта из заявки
        order2 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id,    # Субагент отправляет
            'payer_1_id': subagent_payer.id,
            'partner_2_id': agent.id,       # Агент получает
            'payer_2_id': agent_payer.id,
            'amount': order_amount,
            'currency': currency,
            'wallet_1_id': wallet_agentka.id,
            'wallet_2_id': wallet_agentka.id,
            'comment': f"Обязательство по сделки № {num_zayavka}",
            'zayavka_ids': [(6, 0, [record_id])]
        })
        _logger.info(f"Order 2 (Субагент → Агент) создан, ID: {order2.id}")

        # Создаем контейнер для Order 1 - Долговой для Клиента в RUB
        self._create_money({
            'date': date,
            'partner_id': client.id,
            'currency': 'rub',
            'state': 'debt',
            'wallet_id': wallet_agentka.id,
            'order_id': order1.id,
            **self._get_currency_fields('rub', -total_client)
        })
        _logger.info("Контейнер для Order 1 (на Клиент, Долг) создан")

        # Создаем контейнер для Order 2 - Положительный для Субагента в валюте заявки
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'positive',
            'wallet_id': wallet_agentka.id,
            'order_id': order2.id,
            **self._get_currency_fields(currency, order_amount)
        })
        _logger.info("Контейнер для Order 2 (на Субагент, Положительный) создан")

        _logger.info("Скрипт завершён успешно.")
        return True
    
    