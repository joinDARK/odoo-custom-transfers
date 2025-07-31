# -*- coding: utf-8 -*-
import logging
from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class ZayavkaMethods(models.Model):
    _inherit = 'amanat.zayavka'

    def write(self, vals):
        trigger = vals.get('fin_entry_check', False)
        trigger2 = vals.get('for_khalida_temp', False)
        send_to_reconciliation = vals.get('send_to_reconciliation', False)

        old_values = {}
        if 'extract_delivery_ids' in vals:
            for rec in self:
                old_values[rec.id] = rec.extract_delivery_ids.ids.copy()
        
        old_payment_rule = self.payment_order_rule_id
        old_expense_rule = self.expense_rule_id
        old_money_cost_rule = self.money_cost_rule_id

        res = super().write(vals)  # <-- Исправлено!

        # if vals.get('status', False) == '6':
        #     for rec in self:
        #         _logger.info("Изменился на нужный статус")
        #         rec.run_all_fix_course_automations()

        if 'extract_delivery_ids' in vals:
            _logger.info(f"Обнаружено изменение extract_delivery_ids в vals: {vals.get('extract_delivery_ids')}")
            for rec in self:
                old_ids = set(old_values.get(rec.id, []))
                new_ids = set(rec.extract_delivery_ids.ids)
                _logger.info(f"Заявка {rec.id}: old_ids={old_ids}, new_ids={new_ids}")
                if old_ids != new_ids:
                    _logger.info(f"Изменения обнаружены для заявки {rec.id}, вызываем _on_extract_delivery_ids_changed")
                    rec._on_extract_delivery_ids_changed(old_ids, new_ids)
                else:
                    _logger.info(f"Изменений не обнаружено для заявки {rec.id}")
                rec.run_change_data()

        if 'deal_closed_date' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'сделка закрыта' для заявки {rec.id}")
                _logger.info(f"Старое Правило платежки: {old_payment_rule.name}")
                _logger.info(f"Старое Правило расхода: {old_expense_rule.name}")
                _logger.info(f"Старое Правило себестоимости: {old_money_cost_rule.name}")
                rec.apply_rules_by_deal_closed_date()

        if trigger:
            for rec in self:
                rec.run_all_fin_entry_automations()
                rec.fin_entry_check = False  # сбрасываем галочку после автоматизации

        if send_to_reconciliation:
            for rec in self:
                _logger.info(f"Отправляем в сверку заявку {rec.id}")
                rec.run_all_send_to_reconciliation_automations()
                rec.send_to_reconciliation = False

        if trigger2:
            for rec in self:
                _logger.info(f"Сработал триггер для Халиды для заявки {rec.id}")
                rec.for_khalida_temp = False
                rec.run_for_khalida_automations()

        # Триггер для автоматизации привязки прайс-листов при изменении даты фиксации курса
        if 'rate_fixation_date' in vals:
            for rec in self:
                _logger.info(f"Изменена дата фиксации курса для заявки {rec.id}, запускаем автоматизацию привязки прайс-листов")
                rec.status = '3'
                rec.run_price_list_automation()

        if 'zayavka_attachments' in vals:
            for rec in self:
                rec._analyze_and_log_document_text()

        if 'screen_sber_attachments' in vals:
            for rec in self:
                rec.analyze_screen_sber_images_with_yandex_gpt()

        if 'invoice_attachments' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'invoice_attachments' для заявки {rec.id}")
                rec.invoice_date = fields.Date.today()
                rec.status = '2'

        # ... (остальная логика по датам)
        #         # Получаем все даты из extract_delivery_ids
        #         raw_dates = rec.extract_delivery_ids.mapped('date')
        #         _logger.info(f"===============! Даты из extract_delivery_ids: {raw_dates} !===============")

        #         # Приводим к типу date, фильтруем невалидные
        #         valid_dates = []
        #         for d in raw_dates:
        #             if not d:
        #                 continue
        #             # Если d уже date, оставляем, если строка — пробуем преобразовать
        #             if isinstance(d, str):
        #                 try:
        #                     parsed = Date.from_string(d)
        #                     if parsed:
        #                         valid_dates.append(parsed)
        #                 except Exception as e:
        #                     _logger.warning(f"Ошибка преобразования строки в дату: {d} ({e})")
        #             else:
        #                 valid_dates.append(d)

        #         if valid_dates:
        #             min_date = min(valid_dates)
        #             max_date = max(valid_dates)
        #             rec.date_received_on_pc_payment = min_date
        #             rec.date_agent_on_pc = max_date
        #             _logger.info(f"Ранняя дата: {min_date}, поздняя дата: {max_date}")
        #         else:
        #             _logger.info("Не найдены корректные даты в массиве.")

        return res

    @api.model
    def create(self, vals):
        range_id = vals.get('range_id')
        if not range_id:
            range_rec = self.env['amanat.ranges'].browse(1)
            if range_rec.exists():
                vals['range_id'] = range_rec.id
            else:
                _logger.warning('В таблице "Диапазон" не найдена запись с ID = 1.')

        trigger = vals.get('fin_entry_check', False)
        trigger2 = vals.get('for_khalida_temp', False)
        send_to_reconciliation = vals.get('send_to_reconciliation', False)
        res = super().create(vals)

        # if vals.get('status', False) == '6':
        #     _logger.info("Изменился на нужный статус")
        #     res.run_all_fix_course_automations()

        if trigger:
            # Запуск основной логики (вместо print потом будут скрипты)
            res.run_all_fin_entry_automations()
            res.fin_entry_check = False  # сбрасываем галочку после автоматизации
        
        if send_to_reconciliation:
            _logger.info(f"Отправляем в сверку заявку {res.id}")
            res.run_all_send_to_reconciliation_automations()
            res.send_to_reconciliation = False

        if trigger2:
            _logger.info(f"Сработал триггер для Халиды для заявки {res.id}")
            res.for_khalida_temp = False
            res.run_for_khalida_automations()

        # Триггер для автоматизации привязки прайс-листов при создании с датой фиксации курса
        if vals.get('rate_fixation_date'):
            _logger.info(f"Создана заявка {res.id} с датой фиксации курса, запускаем автоматизацию привязки прайс-листов")
            res.status = '3'
            res.run_price_list_automation()

        # ... (остальная логика по period_id и т.п.)
        if not vals.get('period_id'):
            Period = self.env['amanat.period']
            period = Period.search([('id', '=', 1)], limit=1)
            if not period:
                period = Period.create({
                    'name': '1',
                    'date_1': '2025-03-01',
                    'date_2': '2025-03-21',
                })
            res.period_id = period.id

        if vals.get('zayavka_attachments'):
            res._analyze_and_log_document_text()

        if vals.get('screen_sber_attachments'):
            res.analyze_screen_sber_images_with_yandex_gpt()

        if vals.get('invoice_attachments'):
            res.invoice_date = fields.Date.today()
            res.status = '2'

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
            f"Создан контейнер (money): partner={vals.get('partner_id')}, amount={vals.get('amount')}, currency={vals.get('currency')}, состояние={vals.get('state')}, ордер={vals.get('order_id')}"
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
        else:
            _logger.warning(f"Валюта {currency} не найдена в currency_field_map")

        return result
    
    @staticmethod
    def _get_reconciliation_currency_fields(currency, amount):
        """
        Возвращает словарь с полем валюты и суммой для модели amanat.reconciliation
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

        result = {'sum': amount}

        # Добавляем поле для конкретной валюты
        if currency in currency_field_map:
            result[currency_field_map[currency]] = amount
        else:
            _logger.warning(f"Валюта {currency} не найдена в currency_field_map")

        return result

    def _get_first_payer(self, contragent):
        """Получает первого плательщика контрагента"""
        if contragent and contragent.payer_ids:
            return contragent.payer_ids[0]
        return False

    def action_create_new_zayavka(self):
        """Открывает форму для создания новой заявки"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Новая заявка',
            'res_model': 'amanat.zayavka',
            'view_mode': 'form',
            'target': 'current',
            'context': dict(self.env.context, default_status='1')
        }