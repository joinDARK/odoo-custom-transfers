import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)

class ZayavkaPriceListAutomation(models.Model):
    _inherit = 'amanat.zayavka'

    def run_price_list_automation(self):
        """
        Автоматизация привязки прайс-листов к заявке.
        Аналог скрипта Airtable для поиска и привязки подходящих прайс-листов
        по условиям: дата фиксации курса, плательщик субагента, сумма заявки.
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

        # 4. Поиск подходящей записи в "Прайс лист проведение"
        matched_carrying_out = self._find_matching_carrying_out_record(
            subagent_payers, rate_fixation_date, equivalent_sum, reward_percent
        )

        # 5. Поиск подходящей записи в "Прайс лист Плательщика Прибыль"
        matched_profit = self._find_matching_profit_record(
            subagent_payers, rate_fixation_date, equivalent_sum, reward_percent
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

        _logger.info(f"[PriceList] Заявка {self.id} обновлена: "
                    f"Прайс лист проведение -> {matched_carrying_out.id if matched_carrying_out else 'нет'}, "
                    f"Прайс лист Плательщика Прибыль -> {matched_profit.id if matched_profit else 'нет'}, "
                    f"Прайс лист Партнеры -> {matched_partners.id if matched_partners else 'нет'}")