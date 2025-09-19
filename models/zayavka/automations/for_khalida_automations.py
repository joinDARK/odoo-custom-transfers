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
            equivalent_sum, reward_percent
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

        # Сначала получаем все записи, подходящие по базовым условиям
        base_domain = [
            ('payer_partners', 'in', subagent_payers.ids),
            ('date_start', '<=', payment_date),
            ('date_end', '>=', payment_date),
            ('min_application_amount', '<=', equivalent_sum),
            ('max_application_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
        ]
        
        candidate_records = PriceListCarryingOut.search(base_domain)
        _logger.info(f"[PriceList Carrying Out] Найдено {len(candidate_records)} кандидатов по базовым условиям")
        
        if not candidate_records:
            _logger.warning("[PriceList Carrying Out] В модели нет записей, подходящих по базовым условиям!")
            return None
        
        # Фильтруем кандидатов и вычисляем вес специфичности
        matching_records = []
        
        for record in candidate_records:
            _logger.info(f"[PriceList Carrying Out] Проверяем запись ID={record.id}: {getattr(record, 'name', 'без названия')}")
            
            # Получаем значения полей записи
            contragent_record = getattr(record, 'contragent_zayavka_id', None)
            agent_record = getattr(record, 'agent_zayavka_id', None)
            client_record = getattr(record, 'client_zayavka_id', None)
            currency_record = getattr(record, 'currency_zayavka', None)
            
            # Проверяем совместимость: пустое поле в записи = подходит ЛЮБОЕ значение в заявке
            contragent_ok = (not contragent_record) or (contragent_record and self.contragent_id and contragent_record.id == self.contragent_id.id)
            agent_ok = (not agent_record) or (agent_record and self.agent_id and agent_record.id == self.agent_id.id)
            client_ok = (not client_record) or (client_record and self.client_id and client_record.id == self.client_id.id)
            currency_ok = (not currency_record) or (currency_record and self.currency and currency_record == self.currency)
            
            _logger.info(f"  Контрагент ({contragent_record} vs {self.contragent_id}): {'✓' if contragent_ok else '✗'}")
            _logger.info(f"  Агент ({agent_record} vs {self.agent_id}): {'✓' if agent_ok else '✗'}")
            _logger.info(f"  Клиент ({client_record} vs {self.client_id}): {'✓' if client_ok else '✗'}")
            _logger.info(f"  Валюта ({currency_record} vs {self.currency}): {'✓' if currency_ok else '✗'}")
            
            # Если все условия выполнены, добавляем в список подходящих
            if contragent_ok and agent_ok and client_ok and currency_ok:
                # Вычисляем вес специфичности = количество непустых полей в записи, которые совпадают с заявкой
                specificity_weight = 0
                
                if contragent_record and self.contragent_id and contragent_record.id == self.contragent_id.id:
                    specificity_weight += 1
                if agent_record and self.agent_id and agent_record.id == self.agent_id.id:
                    specificity_weight += 1
                if client_record and self.client_id and client_record.id == self.client_id.id:
                    specificity_weight += 1
                if currency_record and self.currency and currency_record == self.currency:
                    specificity_weight += 1
                
                matching_records.append((record, specificity_weight))
                _logger.info(f"  ✅ Запись подходит! Вес специфичности: {specificity_weight}")
            else:
                _logger.info("  ❌ Запись не подходит")
                
            _logger.info("  " + "-" * 50)
        
        if not matching_records:
            _logger.warning("[PriceList Carrying Out] Не найдено подходящих записей")
            return None
        
        # Сортируем по убыванию веса специфичности (наиболее специфичные первыми)
        matching_records.sort(key=lambda x: x[1], reverse=True)
        
        # Выбираем наиболее специфичную запись
        best_record, best_weight = matching_records[0]
        
        _logger.info(f"[PriceList Carrying Out] ✅ Выбрана наиболее специфичная запись: ID={best_record.id} (название: {getattr(best_record, 'name', 'без названия')}), вес: {best_weight}")
        
        # Логируем все найденные записи для понимания выбора
        if len(matching_records) > 1:
            _logger.info("[PriceList Carrying Out] Другие подходящие записи:")
            for record, weight in matching_records[1:]:
                _logger.info(f"  - ID={record.id} (название: {getattr(record, 'name', 'без названия')}), вес: {weight}")
        
        return best_record 

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
        
        # Сначала получаем все записи, подходящие по базовым условиям
        base_domain = [
            ('payer_subagent_ids', 'in', subagent_payers.ids),
            ('date_start', '<=', payment_date),
            ('date_end', '>=', payment_date),
            ('min_zayavka_amount', '<=', equivalent_sum),
            ('max_zayavka_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
        ]
        
        candidate_records = PriceListProfit.search(base_domain)
        _logger.info(f"[PriceList Profit] Найдено {len(candidate_records)} кандидатов по базовым условиям")
        
        if not candidate_records:
            _logger.warning("[PriceList Profit] В модели нет записей, подходящих по базовым условиям!")
            return None
        
        # Фильтруем кандидатов и вычисляем вес специфичности
        matching_records = []
        
        for record in candidate_records:
            _logger.info(f"[PriceList Profit] Проверяем запись ID={record.id}: {getattr(record, 'name', 'без названия')}")
            
            # Получаем значения полей записи
            contragent_record = getattr(record, 'contragent_zayavka_id', None)
            agent_record = getattr(record, 'agent_zayavka_id', None)
            client_record = getattr(record, 'client_zayavka_id', None)
            currency_record = getattr(record, 'currency_zayavka', None)
            
            # Проверяем совместимость: пустое поле в записи = подходит ЛЮБОЕ значение в заявке
            contragent_ok = (not contragent_record) or (contragent_record and self.contragent_id and contragent_record.id == self.contragent_id.id)
            agent_ok = (not agent_record) or (agent_record and self.agent_id and agent_record.id == self.agent_id.id)
            client_ok = (not client_record) or (client_record and self.client_id and client_record.id == self.client_id.id)
            currency_ok = (not currency_record) or (currency_record and self.currency and currency_record == self.currency)
            
            _logger.info(f"  Контрагент ({contragent_record} vs {self.contragent_id}): {'✓' if contragent_ok else '✗'}")
            _logger.info(f"  Агент ({agent_record} vs {self.agent_id}): {'✓' if agent_ok else '✗'}")
            _logger.info(f"  Клиент ({client_record} vs {self.client_id}): {'✓' if client_ok else '✗'}")
            _logger.info(f"  Валюта ({currency_record} vs {self.currency}): {'✓' if currency_ok else '✗'}")
            
            # Если все условия выполнены, добавляем в список подходящих
            if contragent_ok and agent_ok and client_ok and currency_ok:
                # Вычисляем вес специфичности = количество непустых полей в записи, которые совпадают с заявкой
                specificity_weight = 0
                
                if contragent_record and self.contragent_id and contragent_record.id == self.contragent_id.id:
                    specificity_weight += 1
                if agent_record and self.agent_id and agent_record.id == self.agent_id.id:
                    specificity_weight += 1
                if client_record and self.client_id and client_record.id == self.client_id.id:
                    specificity_weight += 1
                if currency_record and self.currency and currency_record == self.currency:
                    specificity_weight += 1
                
                matching_records.append((record, specificity_weight))
                _logger.info(f"  ✅ Запись подходит! Вес специфичности: {specificity_weight}")
            else:
                _logger.info("  ❌ Запись не подходит")
                
            _logger.info("  " + "-" * 50)
        
        if not matching_records:
            _logger.warning("[PriceList Profit] Не найдено подходящих записей")
            return None
        
        # Сортируем по убыванию веса специфичности (наиболее специфичные первыми)
        matching_records.sort(key=lambda x: x[1], reverse=True)
        
        # Выбираем наиболее специфичную запись
        best_record, best_weight = matching_records[0]
        
        _logger.info(f"[PriceList Profit] ✅ Выбрана наиболее специфичная запись: ID={best_record.id} (название: {getattr(best_record, 'name', 'без названия')}), вес: {best_weight}")
        
        # Логируем все найденные записи для понимания выбора
        if len(matching_records) > 1:
            _logger.info("[PriceList Profit] Другие подходящие записи:")
            for record, weight in matching_records[1:]:
                _logger.info(f"  - ID={record.id} (название: {getattr(record, 'name', 'без названия')}), вес: {weight}")
        
        return best_record 

    def _find_matching_partners_record(self, equivalent_sum, reward_percent):
        """
        Поиск подходящей записи в модели amanat.price_list_partners
        """
        PriceListPartners = self.env['amanat.price_list_partners']

        if not self.rate_fixation_date:
            _logger.warning(f"[PriceList Partners] Пропускаем заявку {self.id}: отсутствует 'Дата фиксации курса'")
            return None
        
        if not self.contragent_id:
            _logger.warning(f"[PriceList Partners] Пропускаем заявку {self.id}: отсутствует 'Контрагент'")
            return None
        
        _logger.info(f"[PriceList Partners] Ищем прайс-лист для заявки {self.id} с датой={self.rate_fixation_date}, контрагент={self.contragent_id.id}, сумма={equivalent_sum}, процент={reward_percent}")
        
        # Сначала получаем все записи, подходящие по базовым условиям
        base_domain = [
            ('contragents_ids', 'in', [self.contragent_id.id]),
            ('date_start', '<=', self.rate_fixation_date),
            ('date_end', '>=', self.rate_fixation_date),
            ('min_application_amount', '<=', equivalent_sum),
            ('max_application_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
        ]
        
        candidate_records = PriceListPartners.search(base_domain)
        _logger.info(f"[PriceList Partners] Найдено {len(candidate_records)} кандидатов по базовым условиям")
        
        if not candidate_records:
            _logger.warning("[PriceList Partners] В модели нет записей, подходящих по базовым условиям!")
            return None
        
        # Фильтруем кандидатов и вычисляем вес специфичности
        matching_records = []
        
        for record in candidate_records:
            _logger.info(f"[PriceList Partners] Проверяем запись ID={record.id}: {getattr(record, 'name', 'без названия')}")
            
            # Получаем значения полей записи
            contragent_record = getattr(record, 'contragent_zayavka_id', None)
            agent_record = getattr(record, 'agent_zayavka_id', None)
            client_record = getattr(record, 'client_zayavka_id', None)
            currency_record = getattr(record, 'currency_zayavka', None)
            
            # Проверяем совместимость: пустое поле в записи = подходит ЛЮБОЕ значение в заявке
            contragent_ok = (not contragent_record) or (contragent_record and self.contragent_id and contragent_record.id == self.contragent_id.id)
            agent_ok = (not agent_record) or (agent_record and self.agent_id and agent_record.id == self.agent_id.id)
            client_ok = (not client_record) or (client_record and self.client_id and client_record.id == self.client_id.id)
            currency_ok = (not currency_record) or (currency_record and self.currency and currency_record == self.currency)
            
            _logger.info(f"  Контрагент ({contragent_record} vs {self.contragent_id}): {'✓' if contragent_ok else '✗'}")
            _logger.info(f"  Агент ({agent_record} vs {self.agent_id}): {'✓' if agent_ok else '✗'}")
            _logger.info(f"  Клиент ({client_record} vs {self.client_id}): {'✓' if client_ok else '✗'}")
            _logger.info(f"  Валюта ({currency_record} vs {self.currency}): {'✓' if currency_ok else '✗'}")
            
            # Если все условия выполнены, добавляем в список подходящих
            if contragent_ok and agent_ok and client_ok and currency_ok:
                # Вычисляем вес специфичности = количество непустых полей в записи, которые совпадают с заявкой
                specificity_weight = 0
                
                if contragent_record and self.contragent_id and contragent_record.id == self.contragent_id.id:
                    specificity_weight += 1
                if agent_record and self.agent_id and agent_record.id == self.agent_id.id:
                    specificity_weight += 1
                if client_record and self.client_id and client_record.id == self.client_id.id:
                    specificity_weight += 1
                if currency_record and self.currency and currency_record == self.currency:
                    specificity_weight += 1
                
                matching_records.append((record, specificity_weight))
                _logger.info(f"  ✅ Запись подходит! Вес специфичности: {specificity_weight}")
            else:
                _logger.info("  ❌ Запись не подходит")
                
            _logger.info("  " + "-" * 50)
        
        if not matching_records:
            _logger.warning("[PriceList Partners] Не найдено подходящих записей")
            return None
        
        # Сортируем по убыванию веса специфичности (наиболее специфичные первыми)
        matching_records.sort(key=lambda x: x[1], reverse=True)
        
        # Выбираем наиболее специфичную запись
        best_record, best_weight = matching_records[0]
        
        _logger.info(f"[PriceList Partners] ✅ Выбрана наиболее специфичная запись: ID={best_record.id} (название: {getattr(best_record, 'name', 'без названия')}), вес: {best_weight}")
        
        # Логируем все найденные записи для понимания выбора
        if len(matching_records) > 1:
            _logger.info("[PriceList Partners] Другие подходящие записи:")
            for record, weight in matching_records[1:]:
                _logger.info(f"  - ID={record.id} (название: {getattr(record, 'name', 'без названия')}), вес: {weight}")
        
        return best_record