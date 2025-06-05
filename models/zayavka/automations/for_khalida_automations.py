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

        # 1. Очищаем ссылки на прайс-листы
        self.price_list_carrying_out_id = False
        self.price_list_profit_id = False
        self.price_list_partners_id = False

        # 2. Извлекаем нужные поля из заявки
        subagent_payers = self.subagent_payer_ids  # many2many
        contractor = self.contragent_id
        rate_fixation_date = self.rate_fixation_date
        equivalent_sum = self.equivalent_amount_usd
        reward_percent = self.reward_percent

        # 3. Поиск прайс-листа "Проведение"
        matched_carrying_out = False
        if subagent_payers:
            PriceListCarryingOut = self.env['amanat.price_list_payer_carrying_out']
            carrying_out_domain = [
                ('payer_partner', 'in', subagent_payers.ids),
                ('date_start', '<=', rate_fixation_date),
                ('date_end', '>=', rate_fixation_date),
            ]
            if equivalent_sum is not None:
                carrying_out_domain += [
                    '|', ('min_application_amount', '=', False), ('min_application_amount', '<=', equivalent_sum),
                    '|', ('max_application_amount', '=', False), ('max_application_amount', '>=', equivalent_sum),
                ]
            matched_carrying_out = PriceListCarryingOut.search(carrying_out_domain, limit=1)
            if matched_carrying_out:
                self.price_list_carrying_out_id = matched_carrying_out.id
                _logger.info(f"[Khalida] Найден прайс-лист Проведение: {matched_carrying_out.id}")
            else:
                _logger.info(f"[Khalida] Не найден прайс-лист Проведение для заявки {self.id}")
        else:
            _logger.info(f"[Khalida] Нет плательщика субагента в заявке {self.id}")

        # 4. Поиск прайс-листа "Прибыль"
        matched_profit = False
        if subagent_payers:
            PriceListProfit = self.env['amanat.price_list_payer_profit']
            profit_domain = [
                ('payer_subagent_ids', 'in', subagent_payers.ids),
                ('date_start', '<=', rate_fixation_date),
                ('date_end', '>=', rate_fixation_date),
            ]
            if equivalent_sum is not None:
                profit_domain += [
                    '|', ('min_zayavka_amount', '=', False), ('min_zayavka_amount', '<=', equivalent_sum),
                    '|', ('max_zayavka_amount', '=', False), ('max_zayavka_amount', '>=', equivalent_sum),
                ]
            matched_profit = PriceListProfit.search(profit_domain, limit=1)
            if matched_profit:
                self.price_list_profit_id = matched_profit.id
                _logger.info(f"[Khalida] Найден прайс-лист Прибыль: {matched_profit.id}")
            else:
                _logger.info(f"[Khalida] Не найден прайс-лист Прибыль для заявки {self.id}")
        else:
            _logger.info(f"[Khalida] Нет плательщика субагента в заявке {self.id}")

        # 5. Поиск прайс-листа "Партнеры"
        matched_partner = False
        if contractor:
            PriceListPartners = self.env['amanat.price_list_partners']
            partners_domain = [
                ('contragents_ids', 'in', contractor.id),
                ('date_start', '<=', rate_fixation_date),
                ('date_end', '>=', rate_fixation_date),
            ]
            if equivalent_sum is not None:
                partners_domain += [
                    '|', ('min_application_amount', '=', False), ('min_application_amount', '<=', equivalent_sum),
                ]
            # Для % вознаграждения (если задан)
            if reward_percent is not None:
                partners_domain += [
                    '|', ('accrual_percentage', '=', False), ('accrual_percentage', '<=', reward_percent)
                ]
            matched_partner = PriceListPartners.search(partners_domain, limit=1)
            if matched_partner:
                self.price_list_partners_id = matched_partner.id
                _logger.info(f"[Khalida] Найден прайс-лист Партнеры: {matched_partner.id}")
            else:
                _logger.info(f"[Khalida] Не найден прайс-лист Партнеры для заявки {self.id}")
        else:
            _logger.info(f"[Khalida] Нет контрагента в заявке {self.id}")

        # 6. Финальный отчет
        _logger.info(f"[Khalida] Итог для заявки {self.id}: Проведение={matched_carrying_out and matched_carrying_out.id or '-'}, Прибыль={matched_profit and matched_profit.id or '-'}, Партнеры={matched_partner and matched_partner.id or '-'}")