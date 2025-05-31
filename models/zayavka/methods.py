# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ZayavkaMethods(models.Model):
    _inherit = 'amanat.zayavka'

    def write(self, vals):
        trigger = vals.get('fin_entry_check', False)
        send_to_reconciliation = vals.get('send_to_reconciliation', False)
        res = super().write(vals)  # <-- Исправлено!

        if trigger:
            for rec in self:
                rec.run_all_fin_entry_automations()
                rec.fin_entry_check = False  # сбрасываем галочку после автоматизации

        if send_to_reconciliation:
            for rec in self:
                _logger.info(f"Отправляем в сверку заявку {rec.id}")
                rec.run_all_send_to_reconciliation_automations()
                rec.send_to_reconciliation = False
        # ... (остальная логика по датам)
        # if 'date_received_on_pc_auto' in vals:
        #     for rec in self:
        #         # Получаем все даты из extract_delivery_ids
        #         dates = rec.extract_delivery_ids.mapped('date')
        #         dates = [d for d in dates if d]
        #         if dates:
        #             min_date = min(dates)
        #             max_date = max(dates)
        #             rec.date_received_on_pc_payment = min_date
        #             rec.date_agent_on_pc = max_date
        return res

    @api.model
    def create(self, vals):
        trigger = vals.get('fin_entry_check', False)
        send_to_reconciliation = vals.get('send_to_reconciliation', False)
        res = super().create(vals)

        if trigger:
            # Запуск основной логики (вместо print потом будут скрипты)
            res.run_all_fin_entry_automations()
            res.fin_entry_check = False  # сбрасываем галочку после автоматизации
        
        if send_to_reconciliation:
            _logger.info(f"Отправляем в сверку заявку {res.id}")
            res.run_all_send_to_reconciliation_automations()
            res.send_to_reconciliation = False
        # ... (остальная логика по period_id и т.п.)
        # if not vals.get('period_id'):
        #     Period = self.env['amanat.period']
        #     period = Period.search([('id', '=', 1)], limit=1)
        #     if not period:
        #         period = Period.create({
        #             'name': '1',
        #             'date_1': '2025-03-01',
        #             'date_2': '2025-03-21',
        #         })
        #     res.period_id = period.id
        return res

    def _clear_related_documents(self):
        """
        Удаляет связанные старые ордера, контейнеры (деньги) и сверки
        для данной заявки (self).
        """
        zayavka = self
        _logger.info(f"Анти-дубль: удаляем старые ордера, контейнеры и сверки для заявки {zayavka.id}")

        # 1. Находим все ордера, связанные с данной заявкой
        orders = self.env['amanat.order'].search([('zayavka_ids', 'in', [zayavka.id])])

        if orders:
            # 2. Удаляем все сверки, связанные с этими ордерами
            reconciliation_domain = [('order_id', 'in', orders.ids)]
            reconciliations = self.env['amanat.reconciliation'].search(reconciliation_domain)
            if reconciliations:
                _logger.info(f"Найдено {len(reconciliations)} сверок, удаляем...")
                reconciliations.unlink()
                _logger.info("Сверки удалены.")

            # 3. Удаляем все контейнеры (деньги), связанные с этими ордерами
            money_domain = [('order_id', 'in', orders.ids)]
            monies = self.env['amanat.money'].search(money_domain)
            if monies:
                _logger.info(f"Найдено {len(monies)} контейнеров, удаляем...")
                monies.unlink()
                _logger.info("Контейнеры удалены.")

            # 4. Удаляем ордера
            _logger.info(f"Ордеров: {len(orders)}, удаляем...")
            orders.unlink()
            _logger.info("Ордеры удалены.")
        else:
            _logger.info("Старых ордеров не обнаружено.")

    def _create_order(self, vals):
        order = self.env['amanat.order'].create(vals)
        _logger.info(f"Создан ордер: {order.name}, сумма={order.amount}, валюта={order.currency}")
        return order

    def _create_money(self, vals):
        money = self.env['amanat.money'].create(vals)
        _logger.info(
            f"Создан контейнер (money): holder={vals.get('holder_id')}, amount={vals.get('amount')}, currency={vals.get('currency')}, состояние={vals.get('state')}, ордер={vals.get('order_id')}"
        )
        return money

    def _create_reconciliation(self, vals):
        reconciliation = self.env['amanat.reconciliation'].create(vals)
        _logger.info(f"Создана сверка: {reconciliation.id}, сумма={reconciliation.sum}, валюта={reconciliation.currency}")
        return reconciliation

    @staticmethod
    def _get_currency_fields(currency, amount):
        """
        Возвращает словарь с полем валюты и суммой для модели amanat.money
        """
        # Маппинг валют на поля в модели money
        currency_field_map = {
            'rub': 'sum_rub',
            'rub_cashe': 'sum_rub_cashe',
            'usd': 'sum_usd',
            'usd_cashe': 'sum_usd_cashe',
            'usdt': 'sum_usdt',
            'euro': 'sum_euro',
            'euro_cashe': 'sum_euro_cashe',
            'cny': 'sum_cny',
            'cny_cashe': 'sum_cny_cashe',
            'aed': 'sum_aed',
            'aed_cashe': 'sum_aed_cashe',
            'thb': 'sum_thb',
            'thb_cashe': 'sum_thb_cashe',
        }

        result = {'amount': amount}

        # Добавляем поле для конкретной валюты
        if currency in currency_field_map:
            result[currency_field_map[currency]] = amount

        return result

    def _get_first_payer(self, contragent):
        """Получает первого плательщика контрагента"""
        if contragent and contragent.payer_ids:
            return contragent.payer_ids[0]
        return False