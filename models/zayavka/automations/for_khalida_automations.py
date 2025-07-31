import logging
from odoo import models, api, _
from odoo.tools import date_utils

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
        rate_fixation_date = self.rate_fixation_date
        equivalent_sum = self.equivalent_amount_usd
        reward_percent = self.reward_percent

        # 3. Проверяем наличие необходимых полей
        if not subagent_payers:
            _logger.warning(f"[PriceList] Пропускаем заявку {self.id}: отсутствует 'Плательщик Субагента' {subagent_payers}")
            return

        if not rate_fixation_date:
            _logger.warning(f"[PriceList] Пропускаем заявку {self.id}: отсутствует 'Дата фиксации курса'")
            return

        if equivalent_sum is None:
            _logger.warning(f"[PriceList] Пропускаем заявку {self.id}: отсутствует 'Сумма эквивалент $'")
            return

        if reward_percent is None:
            _logger.warning(f"[PriceList] Пропускаем заявку {self.id}: отсутствует 'Процент начисления'")
            return

        # Применяем правила
        self.apply_rules_by_deal_closed_date()

        # 4. Поиск подходящей записи в "Прайс лист проведение"
        matched_carrying_out = self._find_matching_carrying_out_record(
            subagent_payers, rate_fixation_date, equivalent_sum
        )

        # 5. Поиск подходящей записи в "Прайс лист Плательщика Прибыль"
        matched_profit = self._find_matching_profit_record(
            subagent_payers, rate_fixation_date, equivalent_sum
        )

        # 6. Поиск подходящей записи в "Прайс лист Партнеры"
        matched_partners = self._find_matching_partners_record(
            subagent_payers, rate_fixation_date, equivalent_sum, reward_percent
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

        _logger.info(f"[PriceList] Заявка {self.id} обновлена: "
                    f"Прайс лист проведение -> {matched_carrying_out.id if matched_carrying_out else 'нет'}, "
                    f"Прайс лист Плательщика Прибыль -> {matched_profit.id if matched_profit else 'нет'}, "
                    f"Прайс лист Партнеры -> {matched_partners.id if matched_partners else 'нет'}")
    
    def _find_matching_carrying_out_record(self, subagent_payers, rate_fixation_date, equivalent_sum):
        """
        Поиск подходящей записи в модели amanat.price_list_payer_carrying_out
        """
        PriceListCarryingOut = self.env['amanat.price_list_payer_carrying_out']
        
        # Строим домен для поиска
        domain = [
            ('payer_partners', 'in', subagent_payers.ids),
            ('date_start', '<=', rate_fixation_date),
            ('date_end', '>=', rate_fixation_date),
        ]

        # Добавляем условия по сумме заявки
        domain += [
            ('min_application_amount', '<=', equivalent_sum),
            ('max_application_amount', '>=', equivalent_sum),
        ]

        # Ищем первую подходящую запись
        matched_record = PriceListCarryingOut.search(domain, limit=1)
        
        if matched_record:
            _logger.info(f"[PriceList] Найден прайс-лист проведение: {matched_record.id}")
        else:
            _logger.info(f"[PriceList] Не найден подходящий прайс-лист проведение для заявки {self.id}")

        return matched_record

    def _find_matching_profit_record(self, subagent_payers, rate_fixation_date, equivalent_sum):
        """
        Поиск подходящей записи в модели amanat.price_list_payer_profit
        """
        PriceListProfit = self.env['amanat.price_list_payer_profit']
        
        # Строим домен для поиска
        domain = [
            ('payer_subagent_ids', 'in', subagent_payers.ids),
            ('date_start', '<=', rate_fixation_date),
            ('date_end', '>=', rate_fixation_date),
        ]

        # Добавляем условия по сумме заявки
        domain += [
            ('min_zayavka_amount', '<=', equivalent_sum),
            ('max_zayavka_amount', '>=', equivalent_sum),
        ]

        # Ищем первую подходящую запись
        matched_record = PriceListProfit.search(domain, limit=1)
        
        if matched_record:
            _logger.info(f"[PriceList] Найден прайс-лист прибыль: {matched_record.id}")
        else:
            _logger.info(f"[PriceList] Не найден подходящий прайс-лист прибыль для заявки {self.id}")

        return matched_record 

    def _find_matching_partners_record(self, subagent_payers, rate_fixation_date, equivalent_sum, reward_percent):
        """
        Поиск подходящей записи в модели amanat.price_list_partners
        """
        PriceListPartners = self.env['amanat.price_list_partners']
        
        # Строим домен для поиска
        domainWithContragent = [
            ('payer_partner', 'in', subagent_payers.ids),
            ('date_start', '<=', rate_fixation_date),
            ('date_end', '>=', rate_fixation_date),
            ('contragent_zayavka_id', '=', self.contragent_id.id),
            ('min_application_amount', '<=', equivalent_sum),
            ('max_application_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
        ]

        # Добавляем условия по сумме заявки
        domain = [
            ('payer_partner', 'in', subagent_payers.ids),
            ('date_start', '<=', rate_fixation_date),
            ('date_end', '>=', rate_fixation_date),
            ('min_application_amount', '<=', equivalent_sum),
            ('max_application_amount', '>=', equivalent_sum),
            ('min_percent_accrual', '<=', reward_percent),
            ('max_percent_accrual', '>=', reward_percent),
        ]

        # Ищем первую подходящую запись
        matched_record = PriceListPartners.search(domainWithContragent, limit=1)
        
        if not matched_record:
            _logger.info(f"[PriceList] Не найден подходящий прайс-лист проведение для заявки {self.id}, ищем общий прайс-лист")
            matched_record = PriceListPartners.search(domain, limit=1)
            
            if matched_record:
                _logger.info(f"[PriceList] Найден общий прайс-лист проведение: {matched_record.id}")
            else:
                _logger.info(f"[PriceList] Не найден подходящий общий прайс-лист проведение для заявки {self.id}")

        return matched_record