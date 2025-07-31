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
        _logger.info(f"[PriceList] Запуск автоматизации привязки прайс-листов для заявки {self.id}")

        # 1. Очищаем поля, чтобы избежать дублирования
        self.price_list_carrying_out_id = False
        self.price_list_profit_id = False
        _logger.info(f"[PriceList] Ссылки в заявке {self.id} очищены")

        # 2. Используем compute-поле subagent_payer_ids напрямую
        subagent_payers = self.subagent_payer_ids
        rate_fixation_date = self.rate_fixation_date
        equivalent_sum = self.equivalent_amount_usd

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

        # 4. Поиск подходящей записи в "Прайс лист проведение"
        matched_carrying_out = self._find_matching_carrying_out_record(
            subagent_payers, rate_fixation_date, equivalent_sum
        )

        # 5. Поиск подходящей записи в "Прайс лист Плательщика Прибыль"
        matched_profit = self._find_matching_profit_record(
            subagent_payers, rate_fixation_date, equivalent_sum
        )

        _logger.info(f"[PriceList] Найден прайс-лист проведение: {matched_carrying_out.name if matched_carrying_out else 'нет'}")
        _logger.info(f"[PriceList] Найден прайс-лист Плательщика Прибыль: {matched_profit.name if matched_profit else 'нет'}")

        # 6. Обновляем заявку ссылками на найденные записи
        update_vals = {}
        if matched_carrying_out:
            update_vals['price_list_carrying_out_id'] = matched_carrying_out.id
        if matched_profit:
            update_vals['price_list_profit_id'] = matched_profit.id

        if update_vals:
            self.write(update_vals)

        _logger.info(f"[PriceList] Заявка {self.id} обновлена: "
                    f"Прайс лист проведение -> {matched_carrying_out.id if matched_carrying_out else 'нет'}, "
                    f"Прайс лист Плательщика Прибыль -> {matched_profit.id if matched_profit else 'нет'}")

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
            '|', ('min_application_amount', '=', False), ('min_application_amount', '<=', equivalent_sum),
            '|', ('max_application_amount', '=', False), ('max_application_amount', '>=', equivalent_sum),
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
            ('date_start', '!=', False),  # date_start не пустая
            ('date_end', '!=', False),    # date_end не пустая
            ('date_start', '<=', rate_fixation_date),  # start <= rateDate
            ('date_end', '>=', rate_fixation_date),    # end >= rateDate
        ]

        # Добавляем условия по сумме заявки
        domain += [
            '|', ('min_zayavka_amount', '=', False), ('min_zayavka_amount', '<=', equivalent_sum),
            '|', ('max_zayavka_amount', '=', False), ('max_zayavka_amount', '>=', equivalent_sum),
        ]

        # Ищем первую подходящую запись
        matched_record = PriceListProfit.search(domain, limit=1)
        
        if matched_record:
            _logger.info(f"[PriceList] Найден прайс-лист прибыль: {matched_record.id} "
                        f"(дата начало: {matched_record.date_start}, дата конец: {matched_record.date_end}) дата фиксации курса: {rate_fixation_date}")
        else:
            _logger.info(f"[PriceList] Не найден подходящий прайс-лист прибыль для заявки {self.id} "
                        f"(дата фиксации курса: {rate_fixation_date})")

        return matched_record 

    