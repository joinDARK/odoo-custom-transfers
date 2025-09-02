import logging
from odoo import models

_logger = logging.getLogger(__name__)

class ForKhalidaAutomations(models.Model):
    _inherit = 'amanat.zayavka'

    def run_for_khalida_automations(self):
        """
        Автоматизация для Халиды: ищет и проставляет подходящие прайс-листы для заявки
        по условиям (дата, плательщик, контрагент, сумма, процент) аналогично скрипту Airtable.
        """
        _logger.info(f"[Khalida] Запуск автоматизации для заявки {self.id}")

        # 1. Очищаем поля, чтобы избежать дублирования
        self.price_list_carrying_out_id = False
        self.price_list_profit_id = False
        self.price_list_partners_id = False

        _logger.info(f"[Khalida] Ссылки в заявке {self.id} очищены")

        # 2. Используем compute-поле subagent_payer_ids напрямую
        subagent_payers = self.subagent_payer_ids
        payment_date = self.payment_date
        equivalent_sum = self.equivalent_amount_usd
        reward_percent = self.reward_percent

        _logger.info(f"[Khalida Automation] Заявка {self.id}: payment_date={payment_date}, equivalent_sum={equivalent_sum}, reward_percent={reward_percent}")

        # Применяем правила по дате фиксации курса (вместо даты закрытия сделки)
        self.apply_rules_by_rate_fixation_date()

        # 3. Проверяем наличие необходимых полей
        if not subagent_payers:
            _logger.warning(f"[PriceList] Пропускаем заявку {self.id}: отсутствует 'Плательщик Субагента' {subagent_payers}")
            return

        if equivalent_sum is None:
            _logger.warning(f"[PriceList] Пропускаем заявку {self.id}: отсутствует 'Сумма эквивалент $'")
            return

        if reward_percent is None:
            _logger.warning(f"[PriceList] Пропускаем заявку {self.id}: отсутствует 'Процент начисления'")
            return

        # 4. Поиск подходящей записи в "Прайс лист проведение"
        # Передаем payment_date, но метод сам проверит его наличие
        matched_carrying_out = self._find_matching_carrying_out_record(
            subagent_payers, None, equivalent_sum, reward_percent
        )

        # 5. Поиск подходящей записи в "Прайс лист Плательщика Прибыль"
        # Передаем payment_date, но метод сам проверит его наличие
        matched_profit = self._find_matching_profit_record(
            subagent_payers, None, equivalent_sum, reward_percent
        )

        # 6. Поиск подходящей записи в "Прайс лист Партнеры"
        matched_partners = self._find_matching_partners_record(
            subagent_payers, equivalent_sum, reward_percent
        )

        # 6. Обновляем заявку ссылками на найденные записи
        update_vals = {}
        if matched_carrying_out:
            update_vals['price_list_carrying_out_id'] = matched_carrying_out.id
        if matched_profit:
            update_vals['price_list_profit_id'] = matched_profit.id
        if matched_partners:
            update_vals['price_list_partners_id'] = matched_partners.id

        if update_vals:
            self.write(update_vals)

        # Логируем результаты с уведомлениями о пропущенных прайс-листах
        carrying_out_msg = matched_carrying_out.id if matched_carrying_out else ('пропущен (нет payment_date)' if not self.payment_date else 'нет')
        profit_msg = matched_profit.id if matched_profit else ('пропущен (нет payment_date)' if not self.payment_date else 'нет')
        partners_msg = matched_partners.id if matched_partners else 'нет'
        
        _logger.info(f"[PriceList] Заявка {self.id} обновлена: "
                    f"Прайс лист проведение -> {carrying_out_msg}, "
                    f"Прайс лист Плательщика Прибыль -> {profit_msg}, "
                    f"Прайс лист Партнеры -> {partners_msg}")
    
    def _find_matching_carrying_out_record(self, subagent_payers, rate_fixation_date, equivalent_sum, reward_percent):
        """
        Поиск подходящей записи в модели amanat.price_list_payer_carrying_out
        Использует payment_date (передано в оплату) вместо rate_fixation_date
        """
        PriceListCarryingOut = self.env['amanat.price_list_payer_carrying_out']

        # Проверяем наличие payment_date, используем rate_fixation_date как fallback
        payment_date = self.payment_date
        if not payment_date:
            # Используем rate_fixation_date как резервную дату
            payment_date = self.rate_fixation_date
            if not payment_date:
                _logger.warning(f"[PriceList Carrying Out] Пропускаем заявку {self.id}: отсутствуют поля 'передано в оплату' (payment_date) и 'дата фиксации курса' (rate_fixation_date)")
                return None
            _logger.info(f"[PriceList Carrying Out] Используем rate_fixation_date={payment_date} как fallback для заявки {self.id}")
        else:
            _logger.info(f"[PriceList Carrying Out] Используем payment_date={payment_date} для заявки {self.id}")
        
        _logger.info(f"[PriceList Carrying Out] Ищем прайс-лист для заявки {self.id} с датой={payment_date}, плательщики={subagent_payers.ids}, сумма={equivalent_sum}, процент={reward_percent}")

        # Строим домен для поиска
        domain = [
            ('payer_partners', 'in', subagent_payers.ids),
            ('date_start', '<=', payment_date),
            ('date_end', '>=', payment_date),
            ('min_application_amount', '<=', equivalent_sum),
            ('max_application_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
        ]
        
        # Подготавливаем значения для гибкого поиска
        if self.contragent_id:
            domain.append('|')  # OR operator
            domain.append(('contragent_zayavka_id', '=', self.contragent_id.id))
            domain.append(('contragent_zayavka_id', '=', False))
        else:
            domain.append(('contragent_zayavka_id', '=', False))
            
        if self.agent_id:
            domain.append('|')  # OR operator
            domain.append(('agent_zayavka_id', '=', self.agent_id.id))
            domain.append(('agent_zayavka_id', '=', False))
        else:
            domain.append(('agent_zayavka_id', '=', False))
            
        if self.client_id:
            domain.append('|')  # OR operator
            domain.append(('client_zayavka_id', '=', self.client_id.id))
            domain.append(('client_zayavka_id', '=', False))
        else:
            domain.append(('client_zayavka_id', '=', False))
            
        if self.currency:
            domain.append('|')  # OR operator
            domain.append(('currency_zayavka', '=', self.currency))
            domain.append(('currency_zayavka', '=', False))
        else:
            domain.append(('currency_zayavka', '=', False))

        softDomain = [
            ('payer_partners', 'in', subagent_payers.ids),
            ('date_start', '<=', payment_date),
            ('date_end', '>=', payment_date),
            ('min_application_amount', '<=', equivalent_sum),
            ('max_application_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
            ('contragent_zayavka_id', '=', False),
            ('agent_zayavka_id', '=', False),
            ('client_zayavka_id', '=', False),
            ('currency_zayavka', '=', False),
        ]

        # Ищем первую подходящую запись
        matched_record = PriceListCarryingOut.search(domain, limit=1)

        if not matched_record:
            _logger.info(f"[PriceList Carrying Out] Не найден подходящий прайс-лист за проведение для заявки {self.id}, ищем по общим условиям")
            matched_record = PriceListCarryingOut.search(softDomain, limit=1)
            
            if not matched_record:
                _logger.warning(f"[PriceList Carrying Out] Не найден подходящий общий прайс-лист за проведение для заявки {self.id}")
                _logger.info(f"[PriceList Carrying Out] Использованный домен: {domain}")
                _logger.info(f"[PriceList Carrying Out] Использованный softDomain: {softDomain}")
                return None
        
        _logger.info(f"[PriceList Carrying Out] Найден прайс-лист за проведение: {matched_record.id} (название: {matched_record.name})")

        return matched_record 

    def _find_matching_profit_record(self, subagent_payers, rate_fixation_date, equivalent_sum, reward_percent):
        """
        Поиск подходящей записи в модели amanat.price_list_payer_profit
        Использует payment_date (передано в оплату) вместо rate_fixation_date
        """
        PriceListProfit = self.env['amanat.price_list_payer_profit']
        
        # Проверяем наличие payment_date, используем rate_fixation_date как fallback
        payment_date = self.payment_date
        if not payment_date:
            # Используем rate_fixation_date как резервную дату
            payment_date = self.rate_fixation_date
            if not payment_date:
                _logger.warning(f"[PriceList Profit] Пропускаем заявку {self.id}: отсутствуют поля 'передано в оплату' (payment_date) и 'дата фиксации курса' (rate_fixation_date)")
                return None
            _logger.info(f"[PriceList Profit] Используем rate_fixation_date={payment_date} как fallback для заявки {self.id}")
        else:
            _logger.info(f"[PriceList Profit] Используем payment_date={payment_date} для заявки {self.id}")
        
        _logger.info(f"[PriceList Profit] Ищем прайс-лист для заявки {self.id} с датой={payment_date}, плательщики={subagent_payers.ids}, сумма={equivalent_sum}, процент={reward_percent}")
        
        # Подготавливаем значения для гибкого поиска
        contragent_values = [False]
        if self.contragent_id:
            contragent_values.append(self.contragent_id.id)
            
        agent_values = [False]
        if self.agent_id:
            agent_values.append(self.agent_id.id)
            
        client_values = [False]
        if self.client_id:
            client_values.append(self.client_id.id)
            
        currency_values = [False]
        if self.currency:
            currency_values.append(self.currency)
        
        # Строим домен для поиска
        domain = [
            ('payer_subagent_ids', 'in', subagent_payers.ids),
            ('date_start', '<=', payment_date),
            ('date_end', '>=', payment_date),
            ('min_zayavka_amount', '<=', equivalent_sum),
            ('max_zayavka_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
        ]

        if self.contragent_id:
            domain.append('|')  # OR operator
            domain.append(('contragent_zayavka_id', '=', self.contragent_id.id))
            domain.append(('contragent_zayavka_id', '=', False))
        else:
            domain.append(('contragent_zayavka_id', '=', False))
            
        if self.agent_id:
            domain.append('|')  # OR operator
            domain.append(('agent_zayavka_id', '=', self.agent_id.id))
            domain.append(('agent_zayavka_id', '=', False))
        else:
            domain.append(('agent_zayavka_id', '=', False))
            
        if self.client_id:
            domain.append('|')  # OR operator
            domain.append(('client_zayavka_id', '=', self.client_id.id))
            domain.append(('client_zayavka_id', '=', False))
        else:
            domain.append(('client_zayavka_id', '=', False))

        if self.currency:
            domain.append('|')  # OR operator
            domain.append(('currency_zayavka', '=', self.currency))
            domain.append(('currency_zayavka', '=', False))
        else:
            domain.append(('currency_zayavka', '=', False))

        softDomain = [
            ('payer_subagent_ids', 'in', subagent_payers.ids),
            ('date_start', '<=', payment_date),
            ('date_end', '>=', payment_date),
            ('min_zayavka_amount', '<=', equivalent_sum),
            ('max_zayavka_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
            ('contragent_zayavka_id', '=', False),
            ('agent_zayavka_id', '=', False),
            ('client_zayavka_id', '=', False),
            ('currency_zayavka', '=', False),
        ]

        # Ищем первую подходящую запись
        matched_record = PriceListProfit.search(domain, limit=1)
        
        if not matched_record:
            _logger.info(f"[PriceList Profit] Не найден подходящий прайс-лист плательщика прибыль для заявки {self.id}, ищем по общим условиям")
            matched_record = PriceListProfit.search(softDomain, limit=1)
            
            if not matched_record:
                _logger.warning(f"[PriceList Profit] Не найден подходящий общий прайс-лист плательщика прибыль для заявки {self.id}")
                _logger.info(f"[PriceList Profit] Использованный домен: {domain}")
                _logger.info(f"[PriceList Profit] Использованный softDomain: {softDomain}")
                return None
        
        _logger.info(f"[PriceList Profit] Найден прайс-лист прибыль: {matched_record.id} (название: {matched_record.name})")

        return matched_record 

    def _find_matching_partners_record(self, subagent_payers, equivalent_sum, reward_percent):
        """
        Поиск подходящей записи в модели amanat.price_list_partners
        """
        PriceListPartners = self.env['amanat.price_list_partners']

        if not self.rate_fixation_date:
            _logger.warning(f"[PriceList Partners] Пропускаем заявку {self.id}: отсутствует 'Дата фиксации курса'")
            return None
        
        # Подготавливаем значения для гибкого поиска
        contragent_values = [False]
        if self.contragent_id:
            contragent_values.append(self.contragent_id.id)
            
        agent_values = [False]
        if self.agent_id:
            agent_values.append(self.agent_id.id)
            
        client_values = [False]
        if self.client_id:
            client_values.append(self.client_id.id)
            
        currency_values = [False]
        if self.currency:
            currency_values.append(self.currency)
        
        # Строим домен для поиска
        domain = [
            ('payer_partner', 'in', subagent_payers.ids),
            ('date_start', '<=', self.rate_fixation_date),
            ('date_end', '>=', self.rate_fixation_date),
            ('min_application_amount', '<=', equivalent_sum),
            ('max_application_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
        ]

        if self.contragent_id:
            domain.append('|')  # OR operator
            domain.append(('contragent_zayavka_id', '=', self.contragent_id.id))
            domain.append(('contragent_zayavka_id', '=', False))
        else:
            domain.append(('contragent_zayavka_id', '=', False))
        
        if self.agent_id:
            domain.append('|')  # OR operator
            domain.append(('agent_zayavka_id', '=', self.agent_id.id))
            domain.append(('agent_zayavka_id', '=', False))
        else:
            domain.append(('agent_zayavka_id', '=', False))
            
        if self.client_id:
            domain.append('|')  # OR operator
            domain.append(('client_zayavka_id', '=', self.client_id.id))
            domain.append(('client_zayavka_id', '=', False))
        else:
            domain.append(('client_zayavka_id', '=', False))
            
        if self.currency:
            domain.append('|')  # OR operator
            domain.append(('currency_zayavka', '=', self.currency))
            domain.append(('currency_zayavka', '=', False))
        else:
            domain.append(('currency_zayavka', '=', False))

        # Добавляем условия по сумме заявки
        softDomain = [
            ('payer_partner', 'in', subagent_payers.ids),
            ('date_start', '<=', self.rate_fixation_date),
            ('date_end', '>=', self.rate_fixation_date),
            ('min_application_amount', '<=', equivalent_sum),
            ('max_application_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
            ('contragent_zayavka_id', '=', False),
            ('agent_zayavka_id', '=', False),
            ('client_zayavka_id', '=', False),
            ('currency_zayavka', '=', False),
        ]

        # Ищем первую подходящую запись
        matched_record = PriceListPartners.search(domain, limit=1)
        
        if not matched_record:
            _logger.info(f"[PriceList] Не найден подходящий прайс-лист партнера для заявки {self.id}, ищем по общим условиям")
            matched_record = PriceListPartners.search(softDomain, limit=1)
            
            if not matched_record:
                _logger.info(f"[PriceList] Не найден подходящий общий прайс-лист партнера для заявки {self.id}")
                return
        
        _logger.info(f"[PriceList] Найден прайс-лист партнера: {matched_record.id}")
        _logger.info(f"[PriceList zayavka] {subagent_payers.ids} {self.rate_fixation_date} {equivalent_sum} {reward_percent} {self.contragent_id.id} {self.agent_id.id} {self.client_id.id} {self.currency}")
        _logger.info(f"[PriceList price_list] {matched_record.payer_partner} {matched_record.date_start} {matched_record.date_end} {matched_record.contragent_zayavka_id} {matched_record.agent_zayavka_id} {matched_record.client_zayavka_id} {matched_record.currency_zayavka} {matched_record.min_application_amount} {matched_record.max_application_amount} {matched_record.min_percent_accrual} {matched_record.max_percent_accrual}")

        return matched_record