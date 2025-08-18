# -*- coding: utf-8 -*-
import logging
import requests
import xml.etree.ElementTree as ET
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

        if 'rate_field' in vals:
            for rec in self:
                rec.status = '3'
                rec.rate_fixation_date = fields.Date.today()

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
                closing_date = vals['deal_closed_date']
                _logger.info(f"[CLOSING_AUTOMATION] Заявка {rec.id}: установлена дата закрытия {closing_date}")
                
                # Устанавливаем статусы для ВСЕХ заявок при закрытии сделки
                rec.swift_status = 'closed'  # Статус SWIFT = "заявка закрыта"
                rec.status = '21'  # 21. Заявка закрыта
                _logger.info(f"[CLOSING_AUTOMATION] Заявка {rec.id}: установлены статусы - status='21', swift_status='closed'")
                
                # Применяем правила управления для всех заявок
                rec.apply_rules_by_deal_closed_date()
                
                # Специфичная автоматизация только для Сбербанка
                contragent_name = rec.contragent_id.name if rec.contragent_id else ""
                if contragent_name and 'сбер' in contragent_name.lower():
                    _logger.info(f"[CLOSING_AUTOMATION] Заявка {rec.id}: контрагент = Сбербанк, запускаем дополнительную автоматизацию")
                    
                    # Генерируем акт-отчет автоматически только для Сбербанка
                    try:
                        _logger.info(f"[CLOSING_AUTOMATION] Заявка {rec.id}: запуск генерации акт-отчета")
                        rec.action_generate_act_report_document()
                        _logger.info(f"[CLOSING_AUTOMATION] Заявка {rec.id}: акт-отчет успешно сгенерирован")
                        
                        # В поле "сделка закрыта" уже установлена дата формирования акт-отчета
                        # (это и есть дата закрытия сделки, которую установил пользователь)
                        _logger.info(f"[CLOSING_AUTOMATION] Заявка {rec.id}: дата формирования акт-отчета = дата закрытия сделки = {closing_date}")
                        
                    except Exception as e:
                        _logger.error(f"[CLOSING_AUTOMATION] Заявка {rec.id}: ошибка генерации акт-отчета: {e}")
                else:
                    _logger.info(f"[CLOSING_AUTOMATION] Заявка {rec.id}: контрагент не Сбербанк ('{contragent_name}'), пропускаем генерацию акт-отчета")
        
        if 'act_report_attachments' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'act_report_attachments' для заявки {rec.id}")
                
                # Проверяем, добавляются ли новые файлы (а не удаляются)
                new_attachments = vals.get('act_report_attachments', [])
                files_added = False
                
                # Анализируем команды для поля Many2many
                for command in new_attachments:
                    if isinstance(command, (list, tuple)) and len(command) >= 1:
                        # Команда (4, id) - добавление существующего файла
                        # Команда (0, 0, {...}) - создание нового файла
                        if command[0] in [4, 0]:
                            files_added = True
                            break
                
                
                rec.status = '21'
        
        if 'swift_received_date' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'swift_received_date' для заявки {rec.id}")
                rec.status = '12'
        
        if 'swift_attachments' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'swift_attachments' для заявки {rec.id}")
                if not vals.get('swift_received_date'):
                    rec.swift_received_date = fields.Date.today()
                rec.status = '12'
                rec.swift_status = 'swift_received'
                
                # Анализируем SWIFT документы для извлечения даты "approved at"
                rec.analyze_swift_documents_for_approved_date()

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
                rec.link_jess_rate = False
                rec.run_link_jess_rate_automation()
                rec.run_price_list_automation()
        
        if vals.get('link_jess_rate', False):
            for rec in self:
                rec.run_link_jess_rate_automation()
                rec.link_jess_rate = False

        if 'zayavka_attachments' in vals:
            for rec in self:
                rec.zayavka_analyse_with_yandex_gpt()

        if 'screen_sber_attachments' in vals:
            for rec in self:
                rec.analyze_screen_sber_images_with_yandex_gpt()

        if 'invoice_attachments' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'invoice_attachments' для заявки {rec.id}")
                rec.invoice_date = fields.Date.today()
                rec.swift_status = 'swift_received'
                rec.status = '2'

        # Анализ документов с YandexGPT (если есть вложения)
        if 'assignment_attachments' in vals:
            for rec in self:
                rec.analyze_assignment_with_yandex_gpt()
                
                # АВТОПОДПИСЬ - выполняется ТОЛЬКО если есть все необходимые условия
                try:
                    _logger.info(f"[METHODS] Detected assignment_attachments change in vals: {vals.keys()}")
                    attachments = rec.assignment_attachments
                    # Проверяем условия для автоподписи
                    should_sign = False
                    if attachments:
                        rec.status = '4'
                        should_sign = rec.should_auto_sign_document(attachments[0])
                    
                    if should_sign:
                        _logger.info(f"[METHODS] Заявка {rec.id}: условия для автоподписи выполнены — запускаем автоподпись СТЕЛЛАР/ТДК")
                        result = rec.auto_sign_assignment_with_stellar()
                        _logger.info(f"[METHODS] Результат автоподписи для заявки {rec.id}: {result}")
                    else:
                        _logger.info(f"[METHODS] Заявка {rec.id}: условия для автоподписи НЕ выполнены — автоподпись пропущена")
                        _logger.info(f"[METHODS] Заявка {rec.id}: выполнен только анализ документов")
                        
                except Exception as e:
                    _logger.error(f"[METHODS] Ошибка проверки/выполнения автоподписи для заявки {rec.id}: {e}")
                    import traceback
                    _logger.error(f"[METHODS] Traceback: {traceback.format_exc()}")
        
        # Изменение статуса при появлении подписанного поручения
        if 'assignment_end_attachments' in vals:
            for rec in self:
                # Проверяем, что есть файлы в assignment_end_attachments
                if rec.assignment_end_attachments:
                    _logger.info(f"[METHODS] Заявка {rec.id}: обнаружены подписанные документы в assignment_end_attachments, устанавливаем статус '4. Подписано поручение'")
                    rec.status = '4'
                else:
                    _logger.info(f"[METHODS] Заявка {rec.id}: поле assignment_end_attachments очищено")
        
        # Возвраты
        if 'cross_return_date' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'cross_return_date' для заявки {rec.id}")
                rec.run_return_payment_to_payer()

        if 'payment_order_date_to_client_account' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'payment_order_date_to_client_account' для заявки {rec.id}")
                rec.run_return_with_main_amount()

        if 'payment_order_date_to_client_account_return_all' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'payment_order_date_to_client_account_return_all' для заявки {rec.id}")
                rec.run_return_with_all_amount_method()
        
        if 'payment_order_date_to_return' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'payment_order_date_to_return' для заявки {rec.id}")
                rec.run_return_with_partial_payment_of_remuneration_method()

        if 'payment_order_date_to_prepayment_of_next' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'payment_order_date_to_prepayment_of_next' для заявки {rec.id}")
                rec.run_return_with_prepayment_of_next_method()

        if 'supplier_currency_paid_date_again_1' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_1' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method()
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission), rec.supplier_currency_paid_date_again_1, rec.payment_date_again_1)
        
        if 'supplier_currency_paid_date_again_2' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_2' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission), rec.supplier_currency_paid_date_again_2, rec.payment_date_again_2)
        
        if 'supplier_currency_paid_date_again_3' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_3' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission), rec.supplier_currency_paid_date_again_3, rec.payment_date_again_3)

        if 'supplier_currency_paid_date_again_4' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_4' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission), rec.supplier_currency_paid_date_again_4, rec.payment_date_again_4)

        if 'supplier_currency_paid_date_again_5' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_5' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission), rec.supplier_currency_paid_date_again_5, rec.payment_date_again_5)

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

        if vals.get('link_jess_rate', False):
            res.run_link_jess_rate_automation()
            res.link_jess_rate = False

        # Триггер для автоматизации привязки прайс-листов при создании с датой фиксации курса
        if vals.get('rate_fixation_date'):
            _logger.info(f"Создана заявка {res.id} с датой фиксации курса, запускаем автоматизацию привязки прайс-листов")
            res.status = '3'
            res.run_link_jess_rate_automation()
            res.link_jess_rate = False
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

        if vals.get('swift_received_date'):
            res.status = '12'

        if vals.get('swift_attachments'):
            if not vals.get('swift_received_date'):
                res.swift_received_date = fields.Date.today()
            res.swift_status = 'swift_received'
            res.status = '12'
            
            # Анализируем SWIFT документы для извлечения даты "approved at"
            res.analyze_swift_documents_for_approved_date()

        if vals.get('deal_closed_date'):
            res.swift_status = 'closed'
            res.status = '21'

        if vals.get('report_attachments'):
            if not vals.get('deal_closed_date'):
                res.deal_closed_date = fields.Date.today()
            res.swift_status = 'closed'
            res.status = '21'

        if vals.get('rate_field'):
            res.status = '3'
            res.rate_fixation_date = fields.Date.today()

        if vals.get('zayavka_attachments'):
            res.zayavka_analyse_with_yandex_gpt()

        if vals.get('screen_sber_attachments'):
            res.analyze_screen_sber_images_with_yandex_gpt()

        if vals.get('invoice_attachments'):
            if not vals.get('swift_received_date'):
                res.swift_received_date = fields.Date.today()
            res.swift_status = 'swift_received'
            res.status = '2'

        # Анализ документов с YandexGPT при создании (если есть вложения)
        if vals.get('assignment_attachments'):
            res.analyze_assignment_with_yandex_gpt()
        
        # Изменение статуса при создании с подписанным поручением
        if vals.get('assignment_end_attachments'):
            _logger.info(f"[CREATE] Заявка {res.id}: создана с подписанными документами в assignment_end_attachments, устанавливаем статус '4. Подписано поручение'")
            res.status = '4'
        
        if vals.get('payment_order_date_to_client_account'):
            _logger.info("Возврат основной суммы")
            res.run_return_with_main_amount()
        
        if vals.get('payment_order_date_to_client_account_return_all'):
            _logger.info("Возврат всей суммы")
            res.run_return_with_all_amount_method()

        if vals.get('payment_order_date_to_return'):
            _logger.info("Возврата с частичной оплатой вознаграждения")
            res.run_return_with_partial_payment_of_remuneration_method()
        
        if vals.get('payment_order_date_to_prepayment_of_next'):
            _logger.info("Возврат на предоплату следующего заказа")
            res.run_return_with_prepayment_of_next_method()
        
        if vals.get('supplier_currency_paid_date_again_1'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method()
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission), res.supplier_currency_paid_date_again_1, res.payment_date_again_1)
        
        if vals.get('supplier_currency_paid_date_again_2'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission), res.supplier_currency_paid_date_again_2, res.payment_date_again_2)

        if vals.get('supplier_currency_paid_date_again_3'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission), res.supplier_currency_paid_date_again_3, res.payment_date_again_3)

        if vals.get('supplier_currency_paid_date_again_4'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission), res.supplier_currency_paid_date_again_4, res.payment_date_again_4)

        if vals.get('supplier_currency_paid_date_again_5'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission), res.supplier_currency_paid_date_again_5, res.payment_date_again_5)

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
        vals['status'] = ''
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

    def action_export_kassa_to_excel(self):
        """Выгружает данные касс для выбранных заявок в Excel"""
        _logger.info(f"🔥 МЕТОД action_export_kassa_to_excel ВЫЗВАН! Количество записей: {len(self)}")
        
        # Проверяем, что есть выбранные записи
        if not self:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "Нет выбранных записей",
                    'message': "Пожалуйста, выберите заявки для выгрузки в Excel",
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Создаем wizard с правильными значениями по умолчанию
        wizard = self.env['amanat.zayavka.kassa.wizard'].create({
            'kassa_type': 'all',
            'field_name': 'date_placement',
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
        })
        
        try:
            # Отправляем выбранные заявки на сервер используя метод wizard'а
            server_response_info = wizard._send_data_to_server(self)
            _logger.info(f"📤 Ответ сервера: {server_response_info}")
            
            # Показываем результат пользователю
            if server_response_info.get('server_status') == 'success':
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': "Успешная выгрузка касс!",
                        'message': f"Выгружено {server_response_info.get('sent_count', 0)} выбранных заявок в Excel",
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': "Ошибка выгрузки",
                        'message': f"Ошибка при выгрузке: {server_response_info.get('server_response', 'Неизвестная ошибка')}",
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        except Exception as e:
            _logger.error(f"❌ Ошибка при выгрузке касс: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "Ошибка выполнения",
                    'message': f"Произошла ошибка: {str(e)}",
                    'type': 'danger',
                    'sticky': True,
                }
            }
        finally:
            # Очищаем временный wizard
            if wizard.exists():
                wizard.unlink()

    def refresh_rates(self):
        """Обновляет курсы инвестинг и ЦБ через API в зависимости от выбранной валюты"""
        console_messages = []
        updated_rates = {}
        
        for record in self:
            currency = record.currency
            console_messages.append(f"🔄 Обновление курсов для заявки {record.zayavka_num or record.id}")
            console_messages.append(f"💱 Выбранная валюта: {currency}")
            
            if not currency:
                console_messages.append("❌ Валюта не выбрана, пропускаем")
                continue
                
            # Маппинг валют для API запросов согласно документации
            currency_map = {
                'usd': ('USD', 'USD/RUB'),
                'euro': ('EUR', 'EUR/RUB'), 
                'cny': ('CNY', 'CNY/RUB'),
                'aed': ('AED', 'AED/RUB'),
                'thb': ('THB', 'THB/RUB'),
                'idr': ('IDR', 'IDR/RUB'),
                'inr': ('INR', 'INR/RUB'),
            }
            
            # Убираем _cashe суффикс если есть
            clean_currency = currency.replace('_cashe', '')
            console_messages.append(f"🧹 Очищенная валюта: {clean_currency}")
            
            if clean_currency not in currency_map:
                console_messages.append(f"⚠️ Валюта {currency} не поддерживается для обновления курсов")
                _logger.warning(f"Валюта {currency} не поддерживается для обновления курсов")
                continue
                
            cbr_currency, investing_pair = currency_map[clean_currency]
            console_messages.append(f"📊 Запрашиваем курсы: ЦБ({cbr_currency}) и Investing({investing_pair})")
            
            # Получаем курс ЦБ
            cbr_rate = None
            cbr_success = False
            try:
                cbr_url = f"http://localhost:8081/api/currency/rate/cbr/{cbr_currency}"
                console_messages.append(f"🌐 Запрос к ЦБ: {cbr_url}")
                
                cbr_response = requests.get(cbr_url, timeout=30, headers={'Accept': 'application/json'})
                cbr_data = cbr_response.json()
                
                console_messages.append(f"📥 Ответ ЦБ: {cbr_data}")
                
                if cbr_data.get('success') and cbr_data.get('rate'):
                    old_rate = record.cb_rate
                    # Заменяем запятую на точку для правильного парсинга float
                    rate_str = str(cbr_data['rate']).replace(',', '.')
                    cbr_rate = float(rate_str)
                    record.cb_rate = cbr_rate
                    console_messages.append(f"✅ Курс ЦБ обновлен: {old_rate} → {cbr_rate}")
                    _logger.info(f"Обновлен курс ЦБ для {cbr_currency}: {cbr_rate}")
                    cbr_success = True
                else:
                    console_messages.append(f"❌ Ошибка получения курса ЦБ: {cbr_data.get('error', 'Неизвестная ошибка')}")
                    _logger.error(f"Ошибка получения курса ЦБ для {cbr_currency}: {cbr_data}")
                    
            except requests.exceptions.RequestException as e:
                console_messages.append(f"🔌 Ошибка запроса к API ЦБ: {str(e)}")
                _logger.error(f"Ошибка запроса к API ЦБ: {e}")
            except (ValueError, KeyError, TypeError) as e:
                console_messages.append(f"🔧 Ошибка обработки ответа ЦБ: {str(e)}")
                _logger.error(f"Ошибка обработки ответа ЦБ: {e}")
                
            # Получаем курс Investing.com
            investing_rate = None
            investing_success = False
            try:
                # URL кодируем пару валют согласно документации
                investing_pair_encoded = investing_pair.replace('/', '%2F')
                investing_url = f"http://localhost:8081/api/currency/rate/investing/{investing_pair_encoded}"
                console_messages.append(f"🌐 Запрос к Investing: {investing_url}")
                
                investing_response = requests.get(investing_url, timeout=30, headers={'Accept': 'application/json'})
                investing_data = investing_response.json()
                
                console_messages.append(f"📥 Ответ Investing: {investing_data}")
                
                if investing_data.get('success') and investing_data.get('rate'):
                    old_rate = record.investing_rate
                    # Заменяем запятую на точку для правильного парсинга float
                    rate_str = str(investing_data['rate']).replace(',', '.')
                    investing_rate = float(rate_str)
                    record.investing_rate = investing_rate
                    console_messages.append(f"✅ Курс Investing обновлен: {old_rate} → {investing_rate}")
                    _logger.info(f"Обновлен курс Investing для {investing_pair}: {investing_rate}")
                    investing_success = True
                else:
                    console_messages.append(f"❌ Ошибка получения курса Investing: {investing_data.get('error', 'Неизвестная ошибка')}")
                    _logger.error(f"Ошибка получения курса Investing для {investing_pair}: {investing_data}")
                    
            except requests.exceptions.RequestException as e:
                console_messages.append(f"🔌 Ошибка запроса к API Investing: {str(e)}")
                _logger.error(f"Ошибка запроса к API Investing: {e}")
            except (ValueError, KeyError, TypeError) as e:
                console_messages.append(f"🔧 Ошибка обработки ответа Investing: {str(e)}")
                _logger.error(f"Ошибка обработки ответа Investing: {e}")
            
            # Принудительно пересчитываем зависимые поля после обновления курсов
            if cbr_success or investing_success:
                old_best_rate_name = record.best_rate_name
                record._compute_best_rate_name()
                console_messages.append(f"BEST_RATE_NAME: {old_best_rate_name} -> {record.best_rate_name}")
                record._compute_best_rate()
                record._compute_effective_rate()
                record._compute_our_client_reward()
                record._compute_client_reward()
                record._compute_non_our_client_reward()
                record._compute_total_client()
                record._compute_partner_post_conversion_rate()
                console_messages.append(f"Пересчитаны зависимые поля для заявки {record.id}")
            
            # Сохраняем обновленные курсы И пересчитанные поля для передачи в JavaScript
            updated_rates[record.id] = {
                'cb_rate': cbr_rate if cbr_success else None,
                'investing_rate': investing_rate if investing_success else None,
                'cbr_success': cbr_success,
                'investing_success': investing_success,
                # Добавляем пересчитанные поля
                'best_rate_name': record.best_rate_name,
                'best_rate': record.best_rate,
                'effective_rate': record.effective_rate,
                'our_client_reward': record.our_client_reward,
                'client_reward': record.client_reward,
                'non_our_client_reward': record.non_our_client_reward,
                'total_client': record.total_client,
                'partner_post_conversion_rate': record.partner_post_conversion_rate,
            }
            
            # Итоговое сообщение для этой заявки
            if cbr_success and investing_success:
                console_messages.append(f"🎉 Все курсы успешно обновлены для заявки {record.zayavka_num}")
            elif cbr_success or investing_success:
                console_messages.append(f"⚠️ Частично обновлены курсы для заявки {record.zayavka_num}")
            else:
                console_messages.append(f"💥 Не удалось обновить курсы для заявки {record.zayavka_num}")
                
            console_messages.append("=" * 50)
                
        # Выводим все сообщения в лог Odoo
        for msg in console_messages:
            _logger.info(msg)
            
        # Создаем сводное уведомление для пользователя
        success_count = len([msg for msg in console_messages if '🎉' in msg or '✅' in msg])
        error_count = len([msg for msg in console_messages if '❌' in msg or '💥' in msg])
        
        if error_count == 0:
            notification_message = "✅ Курсы успешно обновлены!"
            notification_type = 'success'
        elif success_count > 0:
            notification_message = f"⚠️ Частично обновлено. Успешно: {success_count}, Ошибок: {error_count}."
            notification_type = 'warning'
        else:
            notification_message = "❌ Не удалось обновить курсы. Проверьте логи сервера."
            notification_type = 'danger'
            
        return {
            'type': 'ir.actions.client',
            'tag': 'refresh_rates_action',
            'params': {
                'title': 'Обновление курсов',
                'message': notification_message,
                'type': notification_type,
                'sticky': False,
                'console_messages': console_messages,
                'updated_rates': updated_rates  # Передаем обновленные курсы в JavaScript
            }
        }
    
    def action_generate_statement_document(self):
        """Генерация документа заявления по шаблону"""
        try:
            # Проверим значения полей перед генерацией
            _logger.info(f"=== ПРОВЕРКА ПОЛЕЙ ДЛЯ ЗАПИСИ ID {self.id} ===")
            _logger.info(f"exporter_importer_name: '{self.exporter_importer_name}' (тип: {type(self.exporter_importer_name)})")
            _logger.info(f"currency: '{self.currency}' (тип: {type(self.currency)})")
            _logger.info(f"subagent_payer_ids: {self.subagent_payer_ids} (количество: {len(self.subagent_payer_ids)})")
            _logger.info(f"country_id: {self.country_id} (name: '{self.country_id.name if self.country_id else 'None'}')")
            _logger.info(f"beneficiary_address: '{self.beneficiary_address}' (тип: {type(self.beneficiary_address)})")
            _logger.info("=== КОНЕЦ ПРОВЕРКИ ПОЛЕЙ ===")
            
            # Проверим также имена плательщиков субагента
            if self.subagent_payer_ids:
                payer_names = [payer.name for payer in self.subagent_payer_ids]
                _logger.info(f"Имена плательщиков субагента: {payer_names}")
            
            # Дополнительная проверка поля валюты
            if hasattr(self, '_fields') and 'currency' in self._fields:
                field_info = self._fields['currency']
                _logger.info(f"Информация о поле currency: {field_info}")
                if hasattr(field_info, 'selection'):
                    _logger.info(f"Selection валюты: {field_info.selection}")
            
        except Exception as debug_error:
            _logger.error(f"Ошибка при отладке полей: {debug_error}")
        
        try:
            # Ищем шаблон заявления
            template = self.env['template.library'].search([
                ('name', '=', 'Заявление'),
                ('template_type', '=', 'docx')
            ], limit=1)
            
            if not template:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Ошибка',
                        'message': 'Шаблон "Заявление" не найден в библиотеке шаблонов',
                        'type': 'danger',
                        'sticky': True,
                    }
                }
            
            # Подготавливаем данные для подстановки
            template_data = self._prepare_statement_template_data()
            
            # Генерируем документ (используем специальный метод для заявлений)
            generated_file = self._generate_statement_document_from_template(template, template_data)
            
            if generated_file:
                # Создаем attachment
                attachment = self.env['ir.attachment'].create({
                    'name': f'Заявление_{self.zayavka_num or self.zayavka_id}.docx',
                    'type': 'binary',
                    'datas': generated_file,
                    'res_model': self._name,
                    'res_id': self.id,
                    'res_field': 'zayavka_output_attachments',
                    'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                })
                
                # Увеличиваем счетчик использования шаблона
                template.increment_usage()
                
                # Обновляем запись для автообновления интерфейса
                self.env['amanat.zayavka'].browse(self.id).invalidate_recordset()
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'notification': {
                            'title': 'Успешно',
                            'message': f'Документ "{attachment.name}" успешно сгенерирован',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Ошибка',
                        'message': 'Не удалось сгенерировать документ',
                        'type': 'danger',
                        'sticky': True,
                    }
                }
                
        except Exception as e:
            _logger.error(f"Ошибка при генерации документа заявления: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка',
                    'message': f'Ошибка при генерации документа: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_generate_act_report_document(self):
        """Генерация документа акта-отчета по шаблону"""
        try:
            # Проверим значения полей перед генерацией
            _logger.info(f"=== ПРОВЕРКА ПОЛЕЙ ДЛЯ АКТА-ОТЧЕТА ID {self.id} ===")
            _logger.info(f"zayavka_num: '{self.zayavka_num}' (тип: {type(self.zayavka_num)})")
            _logger.info(f"instruction_signed_date: '{self.instruction_signed_date}' (тип: {type(self.instruction_signed_date)})")
            _logger.info(f"client_id: {self.client_id} (name: '{self.client_id.name if self.client_id else 'None'}')")
            _logger.info(f"agent_id: {self.agent_id} (name: '{self.agent_id.name if self.agent_id else 'None'}')")
            _logger.info(f"exporter_importer_name: '{self.exporter_importer_name}'")
            _logger.info(f"contract_number: '{self.contract_number}'")
            _logger.info("=== КОНЕЦ ПРОВЕРКИ ПОЛЕЙ ДЛЯ АКТА ===")
            
        except Exception as debug_error:
            _logger.error(f"Ошибка при отладке полей акта: {debug_error}")
        
        try:
            # Ищем шаблон акта
            template = self.env['template.library'].search([
                ('name', '=', 'Акт'),
                ('template_type', '=', 'docx')
            ], limit=1)
            
            if not template:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Ошибка',
                        'message': 'Шаблон "Акт" не найден в библиотеке шаблонов',
                        'type': 'danger',
                        'sticky': True,
                    }
                }
            
            # Подготавливаем данные для подстановки
            template_data = self._prepare_act_report_template_data()
            
            # Генерируем документ
            generated_file = self._generate_document_from_template(template, template_data)
            
            if generated_file:
                # Создаем attachment
                attachment = self.env['ir.attachment'].create({
                    'name': f'Акт-отчет_{self.zayavka_num or self.zayavka_id}.docx',
                    'type': 'binary',
                    'datas': generated_file,
                    'res_model': self._name,
                    'res_id': self.id,
                    'res_field': 'act_report_attachments',
                    'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                })
                
                # Увеличиваем счетчик использования шаблона
                template.increment_usage()
                
                # Обновляем запись для автообновления интерфейса
                self.env['amanat.zayavka'].browse(self.id).invalidate_recordset()
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'notification': {
                            'title': 'Успешно',
                            'message': f'Документ "{attachment.name}" успешно сгенерирован',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Ошибка',
                        'message': 'Не удалось сгенерировать документ',
                        'type': 'danger',
                        'sticky': True,
                    }
                }
                
        except Exception as e:
            _logger.error(f"Ошибка при генерации акта-отчета: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка',
                    'message': f'Ошибка при генерации документа: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def _prepare_act_report_template_data(self):
        """Подготавливает данные для подстановки в шаблон акта-отчета"""
        from datetime import datetime
        
        # Русские названия месяцев
        russian_months = {
            1: 'Января', 2: 'Февраля', 3: 'Марта', 4: 'Апреля',
            5: 'Мая', 6: 'Июня', 7: 'Июля', 8: 'Августа',
            9: 'Сентября', 10: 'Октября', 11: 'Ноября', 12: 'Декабря'
        }
        
        def format_russian_date(date_obj):
            """Форматирует дату в русском формате: "23" Июля 2025 г."""
            if not date_obj:
                return ""
            try:
                day = date_obj.day
                month = russian_months.get(date_obj.month, date_obj.strftime('%B'))
                year = date_obj.year
                return f'«{day}» {month} {year} г.'
            except (AttributeError, ValueError):
                return str(date_obj)
        
        def format_dot_date(date_obj):
            """Форматирует дату в формате дд.мм.гггг"""
            if not date_obj:
                return ""
            try:
                return date_obj.strftime('%d.%m.%Y')
            except (AttributeError, ValueError):
                return str(date_obj)
        
        def format_amount_with_currency(amount, currency_code):
            """Форматирует сумму с валютой в формате: 403 920,00 USD"""
            if not amount:
                return ""
            try:
                # Форматируем число с разделением тысяч пробелами и двумя знаками после запятой
                formatted_amount = f"{amount:,.2f}".replace(',', ' ').replace('.', ',')
                # Приводим валюту к верхнему регистру
                currency_upper = (currency_code or '').upper()
                return f"{formatted_amount} {currency_upper}".strip()
            except (ValueError, TypeError):
                currency_upper = (currency_code or '').upper()
                return f"{amount} {currency_upper}".strip()
        
        def get_deal_type_text(deal_type):
            """Получает текстовое описание типа сделки"""
            deal_type_mapping = {
                'import': 'Оплата по импортному контракту',
                'export': 'Оплата по экспортному контракту',
            }
            return deal_type_mapping.get(deal_type, deal_type or '')
        
        # Текущая дата для генерации документа
        current_date = datetime.now()
        generation_date_formatted = format_russian_date(current_date)
        
        # Дата подписания поручения
        instruction_date_formatted = format_russian_date(self.instruction_signed_date)
        
        # Номер поручения (только цифры)
        instruction_number = self.instruction_number or ""
        if instruction_number:
            # Оставляем только цифры, убираем все буквы и символы
            import re
            instruction_number = re.sub(r'[^\d]', '', instruction_number)
        
        # Клиент
        client_name = ""
        if self.client_id and self.client_id.name:
            client_name = str(self.client_id.name).strip()
        
        # Агент (НЕ Субагент!)
        agent_name = ""
        if self.agent_id and self.agent_id.name:
            agent_name = str(self.agent_id.name).strip()
        
        # Покупатель/продавец (экспортер/импортер)
        buyer_seller = ""
        if self.exporter_importer_name:
            buyer_seller = str(self.exporter_importer_name).strip()
        
        # Номер контракта
        contract_number = ""
        if self.contract_number:
            contract_number = str(self.contract_number).strip()
        
        # Вид сделки
        deal_type_text = get_deal_type_text(self.deal_type)
        
        # Дата получения SWIFT
        swift_received_formatted = format_dot_date(self.swift_received_date)
        
        # Заявка по курсу в рублях
        application_amount_rub = self.application_amount_rub_contract or 0.0
        application_amount_rub_formatted = f"{application_amount_rub:,.2f}".replace(',', ' ').replace('.', ',')
        
        # Сумма и валюта заявки
        amount_with_currency = format_amount_with_currency(self.amount, self.currency)
        
        # Вознаграждение Сбер
        sber_reward = self.sber_reward or 0.0
        sber_reward_formatted = f"{sber_reward:,.2f}".replace(',', ' ').replace('.', ',')
        
        # Итого Сбер
        total_sber = self.total_sber or 0.0
        total_sber_formatted = f"{total_sber:,.2f}".replace(',', ' ').replace('.', ',')
        
        # Вознаграждение Сбер текстом (с копейками)
        sber_reward_text = self._amount_to_russian_text(sber_reward)
        _logger.info(f"[ПОДИТОГ_ТЕКСТ] sber_reward = {sber_reward}")
        _logger.info(f"[ПОДИТОГ_ТЕКСТ] sber_reward_text = '{sber_reward_text}'")
        
        # Отладочная информация
        _logger.info("=== ДАННЫЕ ДЛЯ АКТА-ОТЧЕТА ===")
        _logger.info(f"instruction_number: '{instruction_number}' (пустое: {not instruction_number})")
        _logger.info(f"generation_date_formatted: '{generation_date_formatted}' (пустое: {not generation_date_formatted})")
        _logger.info(f"instruction_date_formatted: '{instruction_date_formatted}' (пустое: {not instruction_date_formatted})")
        _logger.info(f"client_name: '{client_name}' (пустое: {not client_name})")
        _logger.info(f"agent_name: '{agent_name}'")
        _logger.info(f"buyer_seller: '{buyer_seller}'")
        _logger.info(f"contract_number: '{contract_number}'")
        _logger.info(f"deal_type_text: '{deal_type_text}'")
        _logger.info(f"swift_received_formatted: '{swift_received_formatted}'")
        _logger.info(f"application_amount_rub_formatted: '{application_amount_rub_formatted}'")
        _logger.info(f"amount_with_currency: '{amount_with_currency}'")
        _logger.info(f"sber_reward_formatted: '{sber_reward_formatted}'")
        _logger.info(f"total_sber_formatted: '{total_sber_formatted}'")
        _logger.info(f"sber_reward_text: '{sber_reward_text}'")
        
        # Подготавливаем финальные данные для замены
        final_data = {
            '{{номер_поручения}}': instruction_number,
            '{{дата_генерации_документа}}': generation_date_formatted,
            '{{дата_подписания_поручения}}': instruction_date_formatted,
            '{{клиент}}': client_name,
            '{{агент}}': agent_name,
            '{{покупатель_продавец}}': buyer_seller,
            '{{номер_контракта}}': contract_number,
            '{{вид_сделки}}': deal_type_text,
            '{{получен_swift}}': swift_received_formatted,
            '{{заявка_по_курсу}}': application_amount_rub_formatted,
            '{{сумма_валюта}}': amount_with_currency,
            '{{вознагрождение_сбер}}': sber_reward_formatted,
            '{{итого_сбер}}': total_sber_formatted,
            '{{подитог_текст}}': sber_reward_text,
        }
        
        _logger.info("=== ФИНАЛЬНЫЕ ДАННЫЕ ИЗ ODOO ДЛЯ ЗАМЕНЫ ===")
        filled_count = 0
        empty_count = 0
        
        for key, value in final_data.items():
            has_data = value and str(value).strip()
            if key == '{{подитог_текст}}':
                _logger.info(f"🎯 [ПОДИТОГ_ТЕКСТ] {key}: '{value}' (длина: {len(str(value))}, has_data: {has_data})")
            
            if has_data:
                filled_count += 1
                _logger.info(f"✅ {key}: '{value}' -> БУДЕТ ЗАМЕНЕНО")
            else:
                empty_count += 1
                _logger.info(f"❌ {key}: '{value}' -> ПУСТОЕ, СИГНАТУРА БУДЕТ УДАЛЕНА")
        
        _logger.info(f"=== ИТОГО: {filled_count} полей с данными, {empty_count} пустых полей ===")
        
        return final_data
    
    def _amount_to_russian_text(self, amount):
        """Конвертирует сумму в русский текст с копейками в формате: 89 385,88 (Восемьдесят девять тысяч триста восемдесят пять) руб. 88 копеек"""
        if not amount:
            return ""
        
        try:
            # Импортируем num2words для русского языка
            try:
                from num2words import num2words
            except ImportError:
                _logger.warning("num2words не установлен, возвращаем числовое значение")
                return f"{amount:,.2f} руб.".replace(',', ' ').replace('.', ',')
            
            # Разделяем на рубли и копейки
            rubles = int(amount)
            kopecks = int((amount - rubles) * 100)
            
            # Форматируем числовую сумму
            formatted_amount = f"{amount:,.2f}".replace(',', ' ').replace('.', ',')
            
            # Конвертируем рубли в текст
            try:
                rubles_text = num2words(rubles, lang='ru')
                # Первая буква заглавная
                rubles_text = rubles_text.capitalize()
            except Exception as e:
                rubles_text = str(rubles)
                _logger.warning(f"Не удалось конвертировать {rubles} в текст: {e}")
            
            # Формируем окончание для копеек
            if kopecks % 10 == 1 and kopecks % 100 != 11:
                kopeck_word = "копейка"
            elif kopecks % 10 in [2, 3, 4] and kopecks % 100 not in [12, 13, 14]:
                kopeck_word = "копейки"
            else:
                kopeck_word = "копеек"
            
            # Собираем итоговую строку в требуемом формате
            if kopecks == 0:
                result = f"{formatted_amount} ({rubles_text}) руб."
            else:
                result = f"{formatted_amount} ({rubles_text}) руб. {kopecks:02d} {kopeck_word}"
            
            return result
            
        except Exception as e:
            _logger.error(f"Ошибка при конвертации суммы {amount} в текст: {e}")
            return f"{amount:,.2f} руб.".replace(',', ' ').replace('.', ',')
    
    def _prepare_statement_template_data(self):
        """Подготавливает данные для подстановки в шаблон заявления"""
        from datetime import datetime
        
        # Получаем данные плательщика субагента
        bill_to = ""
        if self.subagent_payer_ids:
            bill_to = ", ".join([payer.name for payer in self.subagent_payer_ids if payer.name])
        
        # Получаем название получателя - обрабатываем False как пустую строку
        beneficiary = ""
        if self.exporter_importer_name:
            beneficiary = str(self.exporter_importer_name).strip()
        
        # Получаем страну
        country = ""
        if self.country_id and hasattr(self.country_id, 'name') and self.country_id.name:
            country = str(self.country_id.name).strip()
        
        # Получаем валюту с правильным отображением
        currency_display = ""
        if self.currency:
            currency_mapping = {
                'rub': 'RUB', 'rub_cashe': 'RUB КЭШ',
                'usd': 'USD', 'usd_cashe': 'USD КЭШ',
                'usdt': 'USDT',
                'euro': 'EURO', 'euro_cashe': 'EURO КЭШ',
                'cny': 'CNY', 'cny_cashe': 'CNY КЭШ',
                'aed': 'AED', 'aed_cashe': 'AED КЭШ',
                'thb': 'THB', 'thb_cashe': 'THB КЭШ',
                'idr': 'IDR', 'idr_cashe': 'IDR КЭШ',
                'inr': 'INR', 'inr_cashe': 'INR КЭШ',
            }
            currency_display = currency_mapping.get(self.currency, self.currency)
        
        # Получаем назначение платежа из правильного поля
        payment_details = self.payment_purpose or "Назначение платежа не указано"
        
        # Отладочная информация - исходные значения полей
        _logger.info("=== ИСХОДНЫЕ ЗНАЧЕНИЯ ПОЛЕЙ ===")
        _logger.info(f"subagent_payer_ids: {self.subagent_payer_ids} (тип: {type(self.subagent_payer_ids)})")
        _logger.info(f"exporter_importer_name: '{self.exporter_importer_name}' (тип: {type(self.exporter_importer_name)})")
        _logger.info(f"country_id: {self.country_id} (тип: {type(self.country_id)})")
        _logger.info(f"beneficiary_address: '{self.beneficiary_address}' (тип: {type(self.beneficiary_address)})")
        _logger.info(f"currency: '{self.currency}' (тип: {type(self.currency)})")
        _logger.info(f"payment_purpose: '{self.payment_purpose}' (тип: {type(self.payment_purpose)})")
        
        # Отладочная информация - обработанные значения
        _logger.info("=== ОБРАБОТАННЫЕ ЗНАЧЕНИЯ ===")
        _logger.info(f"bill_to: '{bill_to}'")
        _logger.info(f"beneficiary: '{beneficiary}'")
        _logger.info(f"country: '{country}'")
        _logger.info(f"currency_display: '{currency_display}'")
        _logger.info(f"payment_details: '{payment_details}'")
        
        # Проверим beneficiary_address отдельно
        beneficiary_addr = str(self.beneficiary_address).strip() if self.beneficiary_address else ""
        _logger.info(f"beneficiary_address обработанный: '{beneficiary_addr}'")
        
        return {
            # Поля которые уже работают (точные совпадения из логов)
            'VALUE DATE*': datetime.now().strftime('%d.%m.%Y'),
            'VALUE DATE *': datetime.now().strftime('%d.%m.%Y'),
            'AMOUNT*': f"{self.amount:.2f}" if self.amount else "0.00",
            'AMOUNT *': f"{self.amount:.2f}" if self.amount else "0.00",
            'CURRENCY*': currency_display,
            'CURRENCY *': currency_display,
            'BILL TO*': bill_to,
            'BILL TO *': bill_to,
            'BENEFICIARY*': beneficiary,
            'BENEFICIARY *': beneficiary,
            'BENEFICIARY COUNTRY*': country,
            'BENEFICIARY COUNTRY *': country,
            'BENEFICIARY ADDRESS*': beneficiary_addr,
            'BENEFICIARY ADDRESS *': beneficiary_addr,
            'ACCOUNT*': self.iban_accc or "",
            'ACCOUNT *': self.iban_accc or "",
            'BENEF.BANK*': self.beneficiary_bank_name or "",
            'BENEF.BANK *': self.beneficiary_bank_name or "",
            'ADDRESS*': self.bank_address or "",
            'ADDRESS *': self.bank_address or "", 
            'SWIFT*': self.bank_swift or "",
            'SWIFT *': self.bank_swift or "",
            'PAYMENT DETAILS*': payment_details,
            'PAYMENT DETAILS *': payment_details,
        }
    
    def _generate_document_from_template(self, template, template_data):
        """Генерирует документ из шаблона с подстановкой данных"""
        import base64
        import tempfile
        import os
        
        try:
            # Декодируем файл шаблона
            template_bytes = base64.b64decode(template.template_file)
            
            # Создаем временный файл для работы
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(template_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Обрабатываем DOCX файл
                result_bytes = self._process_docx_template(temp_file_path, template_data)
                return base64.b64encode(result_bytes).decode('utf-8')
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            _logger.error(f"Ошибка при генерации документа из шаблона: {str(e)}")
            return None
    
    def _generate_statement_document_from_template(self, template, template_data):
        """Генерирует документ заявления из шаблона с заполнением таблиц"""
        import base64
        import tempfile
        import os
        
        try:
            # Декодируем файл шаблона
            template_bytes = base64.b64decode(template.template_file)
            
            # Создаем временный файл для работы
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(template_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Обрабатываем DOCX файл специальным методом для таблиц
                result_bytes = self._process_statement_docx_template(temp_file_path, template_data)
                if result_bytes:
                    return base64.b64encode(result_bytes).decode('utf-8')
                else:
                    return None
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            _logger.error(f"Ошибка при генерации документа заявления из шаблона: {str(e)}")
            return None
    
    def _process_docx_template(self, docx_path, template_data):
        """Обрабатывает DOCX шаблон, заменяя сигнатуры на значения"""
        import tempfile
        import os
        from zipfile import ZipFile
        
        try:
            _logger.info(f"[_process_docx_template] Начинаем обработку шаблона: {docx_path}")
            
            # Создаем временную папку для распаковки
            with tempfile.TemporaryDirectory() as temp_dir:
                # Распаковываем DOCX
                with ZipFile(docx_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Обрабатываем document.xml
                document_path = os.path.join(temp_dir, 'word', 'document.xml')
                if os.path.exists(document_path):
                    # Читаем содержимое XML как строку для простой замены
                    with open(document_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    _logger.info("=== ОТЛАДКА DOCX ОБРАБОТКИ ===")
                    _logger.info(f"Данные для замены: {template_data}")
                    _logger.info(f"Размер XML содержимого: {len(content)} символов")
                    
                    # Покажем небольшой образец содержимого для анализа
                    preview_start = content[:300].replace('\n', '\\n').replace('\r', '\\r')
                    _logger.info(f"Начало XML: {preview_start}...")
                    
                    # Счетчик замен
                    total_replacements = 0
                    
                    # Экранируем XML символы в значениях И фигурные скобки (чтобы они не воспринимались как новые сигнатуры)
                    def escape_xml(text):
                        """Экранирует XML символы и фигурные скобки в значениях"""
                        if not isinstance(text, str):
                            text = str(text)
                        return (text.replace('&', '&amp;')
                               .replace('"', '&quot;')
                               .replace("'", '&apos;')
                               .replace('{', '&#123;')
                               .replace('}', '&#125;'))
                        # НЕ экранируем круглые скобки - они не являются специальными XML-символами
                    
                    # Сначала найдем все сигнатуры в документе с помощью regex
                    import re
                    
                    # Убираем XML-теги для поиска сигнатур
                    clean_text = re.sub(r'<[^>]+>', '', content)
                    signature_pattern = r'\{\{[^}]+\}\}'  # Ищем все {{что-то}}
                    bracket_pattern = r'\[[^\]]+\]'  # Ищем все [что-то]
                    found_signatures = re.findall(signature_pattern, clean_text)
                    found_bracket_signatures = re.findall(bracket_pattern, clean_text)
                    _logger.info(f"Найдены сигнатуры в очищенном тексте: {found_signatures}")
                    _logger.info(f"Найдены квадратные сигнатуры: {found_bracket_signatures}")
                    
                    # Специальная проверка для подитог_текст (фигурные и квадратные скобки)
                    if '{{подитог_текст}}' in found_signatures:
                        _logger.info(f"🎯 [ПОДИТОГ_ТЕКСТ] Сигнатура '{{подитог_текст}}' НАЙДЕНА в документе!")
                    elif '[подитог_текст]' in found_bracket_signatures:
                        _logger.info(f"🎯 [ПОДИТОГ_ТЕКСТ] Квадратная сигнатура '[подитог_текст]' НАЙДЕНА в документе!")
                    else:
                        _logger.info(f"❌ [ПОДИТОГ_ТЕКСТ] Сигнатура '{{подитог_текст}}' или '[подитог_текст]' НЕ НАЙДЕНА в документе")
                        _logger.info(f"❌ [ПОДИТОГ_ТЕКСТ] Проверяем похожие сигнатуры:")
                        for sig in found_signatures + found_bracket_signatures:
                            if 'подитог' in sig.lower() or 'текст' in sig.lower():
                                _logger.info(f"❌ [ПОДИТОГ_ТЕКСТ] Похожая сигнатура: '{sig}'")
                    
                    # Также найдем разбитые сигнатуры в XML
                    fragmented_pattern = r'\{\{[^}]*</[^>]+>[^{}]*\}\}'
                    fragmented_signatures = re.findall(fragmented_pattern, content)
                    _logger.info(f"Найдены разбитые сигнатуры в XML: {fragmented_signatures}")
                    
                    # Создаем маппинг найденных сигнатур к нашим данным
                    signature_mapping = {}
                    
                    # Сначала обрабатываем фигурные скобки {{}}
                    for found_sig in found_signatures:
                        # Попробуем сопоставить с нашими данными
                        if found_sig in template_data:
                            signature_mapping[found_sig] = template_data[found_sig]
                        else:
                            # Попробуем найти по содержимому (например {{Т-13488}} -> номер поручения)
                            inner_text = found_sig.strip('{}')
                            
                            # Специальные случаи для известных сигнатур (проверяем точные совпадения ПЕРВЫМИ)
                            if inner_text == 'подитог_текст':
                                signature_mapping[found_sig] = template_data.get('{{подитог_текст}}', '')
                                _logger.info(f"🎯 [ПОДИТОГ_ТЕКСТ] ТОЧНОЕ СОВПАДЕНИЕ: '{found_sig}' -> '{template_data.get('{{подитог_текст}}', '')}')")
                                _logger.info(f"🎯 [ПОДИТОГ_ТЕКСТ] Длина значения: {len(str(template_data.get('{{подитог_текст}}', '')))}")
                            elif inner_text == 'вознагрождение_сбер':
                                signature_mapping[found_sig] = template_data.get('{{вознагрождение_сбер}}', '')
                                _logger.info(f"🎯 ТОЧНОЕ СОВПАДЕНИЕ для вознагрождение_сбер: '{found_sig}' -> '{template_data.get('{{вознагрождение_сбер}}', '')}')")
                            elif inner_text == 'итого_сбер':
                                signature_mapping[found_sig] = template_data.get('{{итого_сбер}}', '')
                            elif inner_text == 'вид_сделки':
                                signature_mapping[found_sig] = template_data.get('{{вид_сделки}}', '')
                            elif inner_text == 'получен_swift':
                                signature_mapping[found_sig] = template_data.get('{{получен_swift}}', '')
                            elif any(char.isdigit() for char in inner_text) and 'Т-' in inner_text:
                                # Это похоже на номер поручения
                                signature_mapping[found_sig] = template_data.get('{{номер_поручения}}', '')
                            elif inner_text in ['ТДК', 'СТЕЛЛАР']:
                                # Это агент
                                signature_mapping[found_sig] = template_data.get('{{агент}}', '')
                            elif 'Августа' in inner_text or 'г.' in inner_text:
                                # Это дата
                                signature_mapping[found_sig] = template_data.get('{{дата_генерации_документа}}', '')
                            elif any(word in inner_text for word in ['Транзакции', 'Расчеты']):
                                # Это клиент
                                signature_mapping[found_sig] = template_data.get('{{клиент}}', '')
                            elif 'ZHEJIANG' in inner_text or 'INDUSTRY' in inner_text:
                                # Это покупатель/продавец
                                signature_mapping[found_sig] = template_data.get('{{покупатель_продавец}}', '')
                            elif 'DM-' in inner_text or 'контракт' in inner_text:
                                # Это номер контракта
                                signature_mapping[found_sig] = template_data.get('{{номер_контракта}}', '')
                            elif 'CNY' in inner_text or '$' in inner_text:
                                # Это сумма с валютой
                                signature_mapping[found_sig] = template_data.get('{{сумма_валюта}}', '')
                            elif any(char.isdigit() for char in inner_text) and (',' in inner_text or '.' in inner_text):
                                # Это числовое значение
                                if 'сбер' in found_sig.lower():
                                    if 'текст' in found_sig.lower():
                                        signature_mapping[found_sig] = template_data.get('{{подитог_текст}}', '')
                                        _logger.info(f"🎯 ЧИСЛОВАЯ ЛОГИКА для подитог_текст: '{found_sig}' -> '{template_data.get('{{подитог_текст}}', '')}')")
                                    elif 'итого' in found_sig.lower():
                                        signature_mapping[found_sig] = template_data.get('{{итого_сбер}}', '')
                                        _logger.info(f"🎯 ЧИСЛОВАЯ ЛОГИКА для итого_сбер: '{found_sig}' -> '{template_data.get('{{итого_сбер}}', '')}')")
                                    else:
                                        signature_mapping[found_sig] = template_data.get('{{вознагрождение_сбер}}', '')
                                        _logger.info(f"🎯 ЧИСЛОВАЯ ЛОГИКА для вознагрождение_сбер: '{found_sig}' -> '{template_data.get('{{вознагрождение_сбер}}', '')}')")
                                else:
                                    signature_mapping[found_sig] = template_data.get('{{заявка_по_курсу}}', '')
                            else:
                                # Если не можем определить тип, оставляем пустым - удалим сигнатуру
                                signature_mapping[found_sig] = ''
                    
                    # Теперь обрабатываем квадратные скобки []
                    for bracket_sig in found_bracket_signatures:
                        # Убираем квадратные скобки и проверяем содержимое
                        inner_text = bracket_sig.strip('[]')
                        
                        if inner_text == 'подитог_текст':
                            signature_mapping[bracket_sig] = template_data.get('{{подитог_текст}}', '')
                            _logger.info(f"🎯 [КВАДРАТНАЯ СКОБКА] ТОЧНОЕ СОВПАДЕНИЕ для подитог_текст: '{bracket_sig}' -> '{template_data.get('{{подитог_текст}}', '')}')")
                        else:
                            # Для других квадратных скобок пока оставляем пустыми
                            signature_mapping[bracket_sig] = ''
                            _logger.info(f"❌ [КВАДРАТНАЯ СКОБКА] Неизвестная сигнатура: '{bracket_sig}'")
                    
                    _logger.info(f"=== СОПОСТАВЛЕНИЕ СИГНАТУР ИЗ ДОКУМЕНТА С ДАННЫМИ ODOO ===")
                    _logger.info(f"Найдено сигнатур в документе: {len(signature_mapping)}")
                    _logger.info(f"Доступно данных из Odoo: {len(template_data)}")
                    
                    # Детальная отладка каждой сигнатуры
                    for sig, val in signature_mapping.items():
                        has_data = val and str(val).strip()
                        if has_data:
                            _logger.info(f"✅ '{sig}' -> '{val}' (ЗАМЕНИМ)")
                        else:
                            _logger.info(f"❌ '{sig}' -> '{val}' (УДАЛИМ)")
                    
                    # Заменяем каждую найденную сигнатуру
                    for signature, value in signature_mapping.items():
                        # Если значение пустое - просто убираем сигнатуру
                        if not value or str(value).strip() == "":
                            _logger.info(f"[ПУСТОЕ ЗНАЧЕНИЕ] Убираем сигнатуру: '{signature}' (значение: '{value}')")
                            # Используем regex для удаления разбитых сигнатур
                            inner_text = signature.strip('{}')
                            # Паттерн для поиска разбитой сигнатуры с XML-тегами внутри
                            pattern = r'\{\{[^}]*?(?:<[^>]*>)*?' + re.escape(inner_text) + r'(?:<[^>]*>)*?[^}]*?\}\}'
                            matches = re.findall(pattern, content, re.DOTALL)
                            for match in matches:
                                content = content.replace(match, "")
                                total_replacements += 1
                                _logger.info(f"Убрали разбитую сигнатуру: '{match[:100]}...'")
                            
                            # Также попробуем простую замену для целых сигнатур
                            if signature in content:
                                content = content.replace(signature, "")
                                total_replacements += 1
                                _logger.info(f"Убрали целую сигнатуру: '{signature}'")
                            continue
                        
                        # Экранируем значение для безопасности XML
                        safe_value = escape_xml(str(value))
                        
                        # Ищем ТОЛЬКО сигнатуры в фигурных скобках (не обычный текст)
                        signature_variants = [
                            signature,  # {{номер_поручения}}
                            signature.replace('{', '&#123;').replace('}', '&#125;'),  # &#123;&#123;номер_поручения&#125;&#125;
                        ]
                        
                        # ВАЖНО: НЕ заменяем обычный текст без фигурных скобок!
                        
                        replaced = False
                        
                        # Сначала пробуем найти разбитую сигнатуру с помощью regex
                        inner_text = signature.strip('{}')
                        # Паттерн для поиска разбитой сигнатуры с XML-тегами внутри
                        pattern = r'\{\{[^}]*?(?:<[^>]*>)*?' + re.escape(inner_text) + r'(?:<[^>]*>)*?[^}]*?\}\}'
                        matches = re.findall(pattern, content, re.DOTALL)
                        
                        for match in matches:
                            _logger.info(f"[НАЙДЕНА РАЗБИТАЯ] Сигнатура: '{match[:100]}...' -> заменяем на '{safe_value}'")
                            content = content.replace(match, safe_value)
                            total_replacements += 1
                            _logger.info(f"[УСПЕШНАЯ ЗАМЕНА РАЗБИТОЙ] '{match[:50]}...' -> '{safe_value}'")
                            replaced = True
                        
                        # Если не нашли разбитую, пробуем обычную замену
                        if not replaced:
                            for variant in signature_variants:
                                if variant in content:
                                    _logger.info(f"[НАЙДЕНА ЦЕЛАЯ] Сигнатура: '{variant}' -> заменяем на '{safe_value}'")
                                    # Подсчитываем количество замен ДО замены
                                    replacements_count = content.count(variant)
                                    if replacements_count > 0:
                                        # Используем точную замену
                                        content = content.replace(variant, safe_value)
                                        total_replacements += replacements_count
                                        _logger.info(f"[УСПЕШНАЯ ЗАМЕНА ЦЕЛОЙ] '{variant}' -> '{safe_value}' ({replacements_count} раз)")
                                        replaced = True
                                        break
                        
                        if not replaced:
                            # Попробуем найти разбитую сигнатуру
                            replaced_content = self._replace_broken_signature(content, signature, safe_value, escape_xml)
                            if replaced_content != content:
                                content = replaced_content
                                total_replacements += 1
                                _logger.info(f"ЗАМЕНА РАЗБИТОЙ СИГНАТУРЫ! '{signature}' -> '{safe_value}'")
                            else:
                                _logger.info(f"НЕТ ЗАМЕНЫ для '{signature}' - сигнатура не найдена в документе")
                    
                    _logger.info(f"=== ИТОГИ ОБРАБОТКИ СИГНАТУР ===")
                    _logger.info(f"Всего выполнено замен: {total_replacements}")
                    
                    # Проверяем, остались ли необработанные сигнатуры (исключаем уже замененные значения)
                    all_signatures = re.findall(r'\{\{[^}]+\}\}', content)
                    all_bracket_signatures = re.findall(r'\[[^\]]+\]', content)
                    remaining_signatures = []
                    
                    # Обрабатываем фигурные скобки
                    for sig in all_signatures:
                        # Пропускаем сигнатуры, которые содержат экранированные фигурные скобки (это уже замененные значения)
                        if ('&#123;' in sig or '&#125;' in sig or '&amp;' in sig or '&quot;' in sig or '&apos;' in sig):
                            _logger.info(f"🔒 Пропускаем уже замененное значение: '{sig[:50]}...' (содержит экранированные символы)")
                            continue
                        remaining_signatures.append(sig)
                    
                    # Добавляем квадратные скобки к оставшимся сигнатурам
                    for bracket_sig in all_bracket_signatures:
                        remaining_signatures.append(bracket_sig)
                    if remaining_signatures:
                        _logger.warning(f"⚠️  ОСТАЛИСЬ НЕОБРАБОТАННЫЕ СИГНАТУРЫ: {len(remaining_signatures)} штук")
                        _logger.info("🧹 Начинаем агрессивную очистку оставшихся сигнатур...")
                        
                        # Агрессивная очистка всех оставшихся сигнатур
                        cleaned_count = 0
                        for remaining_sig in remaining_signatures:
                            if remaining_sig in content:
                                # Попробуем найти ключевые слова для определения типа
                                clean_sig = re.sub(r'<[^>]+>', '', remaining_sig)
                                # Убираем фигурные или квадратные скобки
                                if remaining_sig.startswith('[') and remaining_sig.endswith(']'):
                                    inner_content = clean_sig.strip('[]')
                                    _logger.info(f"🔧 [АГРЕССИВНАЯ КВАДРАТНАЯ] Обрабатываем: '{remaining_sig}' -> внутренний текст: '{inner_content}'")
                                else:
                                    inner_content = clean_sig.strip('{}')
                                
                                # Определяем значение по ключевым словам
                                replacement_value = ""
                                if inner_content == 'подитог_текст':
                                    replacement_value = template_data.get('{{подитог_текст}}', '')
                                    _logger.info(f"🔧 [АГРЕССИВНАЯ КВАДРАТНАЯ] ТОЧНОЕ СОВПАДЕНИЕ для подитог_текст: '{remaining_sig}' -> '{replacement_value}'")
                                elif 'дата_подписания' in inner_content:
                                    replacement_value = template_data.get('{{дата_подписания_поручения}}', '')
                                elif 'контракт' in inner_content:
                                    replacement_value = template_data.get('{{номер_контракта}}', '')
                                elif 'вид' in inner_content and 'сделк' in inner_content:
                                    replacement_value = template_data.get('{{вид_сделки}}', '')
                                elif 'получен' in inner_content and 'swift' in inner_content:
                                    replacement_value = template_data.get('{{получен_swift}}', '')
                                elif 'вознагрождение' in inner_content and 'сбер' in inner_content:
                                    if 'текст' in inner_content:
                                        replacement_value = template_data.get('{{подитог_текст}}', '')
                                        _logger.info(f"🔧 АГРЕССИВНАЯ ЗАМЕНА для подитог_текст: '{clean_sig}' -> '{replacement_value}'")
                                    else:
                                        replacement_value = template_data.get('{{вознагрождение_сбер}}', '')
                                        _logger.info(f"🔧 АГРЕССИВНАЯ ЗАМЕНА для вознагрождение_сбер: '{clean_sig}' -> '{replacement_value}'")
                                elif 'итого' in inner_content and 'сбер' in inner_content:
                                    replacement_value = template_data.get('{{итого_сбер}}', '')
                                
                                # Заменяем или удаляем
                                if replacement_value and str(replacement_value).strip():
                                    content = content.replace(remaining_sig, escape_xml(str(replacement_value)))
                                    _logger.info(f"🔧 Агрессивно заменили: '{clean_sig}' -> '{replacement_value}'")
                                else:
                                    content = content.replace(remaining_sig, "")
                                    _logger.info(f"🗑️  Агрессивно удалили: '{clean_sig}'")
                                
                                cleaned_count += 1
                                total_replacements += 1
                        
                        _logger.info(f"🧹 Агрессивная очистка завершена: обработано {cleaned_count} сигнатур")
                        
                        # Финальная проверка
                        final_remaining = re.findall(r'\{\{[^}]+\}\}', content)
                        if final_remaining:
                            _logger.warning(f"⚠️  ВСЕГО ОСТАЕТСЯ НЕОБРАБОТАННЫХ: {len(final_remaining)} сигнатур")
                        else:
                            _logger.info("✅ Все сигнатуры успешно обработаны после агрессивной очистки!")
                    else:
                        _logger.info("✅ Все сигнатуры успешно обработаны!")
                    
                    _logger.info("=== КОНЕЦ ОБРАБОТКИ СИГНАТУР ===")
                    
                    # Проверяем валидность XML перед сохранением
                    try:
                        ET.fromstring(content)
                        _logger.info("XML валидация прошла успешно")
                    except ET.ParseError as e:
                        _logger.error(f"XML поврежден после замены: {e}")
                        _logger.error("Попробуем восстановить...")
                        # В случае ошибки, попробуем более простой подход
                        _logger.info("Пробуем альтернативный метод замены...")
                        with open(document_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Простая замена без regex
                        for signature, value in template_data.items():
                            # Если значение пустое - просто убираем сигнатуру
                            if not value or str(value).strip() == "":
                                # Ищем ТОЛЬКО сигнатуры в фигурных скобках (НЕ обычный текст!)
                                signature_variants = [
                                    signature,  # {{номер_поручения}}
                                    signature.replace('{', '&#123;').replace('}', '&#125;'),  # &#123;&#123;номер_поручения&#125;&#125;
                                ]
                                # НЕ добавляем signature.strip('{}') чтобы не удалять обычный текст!
                                for variant in signature_variants:
                                    if variant in content:
                                        content = content.replace(variant, "")
                                        _logger.info(f"Убираем пустую сигнатуру: {variant}")
                                        break
                                continue
                                
                            safe_value = escape_xml(str(value))
                            
                            # Ищем ТОЛЬКО сигнатуры в фигурных скобках (не обычный текст)
                            signature_variants = [
                                signature,  # {{номер_поручения}}
                                signature.replace('{', '&#123;').replace('}', '&#125;'),  # &#123;&#123;номер_поручения&#125;&#125;
                            ]
                            
                            # ВАЖНО: НЕ заменяем обычный текст без фигурных скобок!
                            
                            for variant in signature_variants:
                                if variant in content:
                                    content = content.replace(variant, safe_value)
                                    _logger.info(f"Простая замена: {variant} -> {safe_value}")
                                    break
                        
                        # Проверяем еще раз
                        try:
                            ET.fromstring(content)
                            _logger.info("XML валидация после простой замены прошла успешно")
                        except ET.ParseError as e2:
                            _logger.error(f"XML все еще поврежден: {e2}")
                            # Возвращаем оригинальный контент
                            with open(document_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            _logger.info("Возвращен оригинальный контент без изменений")
                    
                    _logger.info("=== КОНЕЦ ОТЛАДКИ DOCX ===")
                    
                    # Сохраняем изменения
                    with open(document_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                # Создаем новый DOCX файл
                result_path = os.path.join(temp_dir, 'result.docx')
                with ZipFile(result_path, 'w') as zip_ref:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file != 'result.docx':
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, temp_dir)
                                zip_ref.write(file_path, arcname)
                
                # Читаем результат
                with open(result_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            _logger.error(f"[_process_docx_template] Ошибка обработки DOCX: {e}")
            import traceback
            _logger.error(f"[_process_docx_template] Traceback: {traceback.format_exc()}")
            return None
    
    def _replace_broken_signature(self, xml_content, signature, value, escape_xml_func):
        """Заменяет сигнатуру, которая может быть разбита на несколько XML элементов"""
        import re
        
        try:
            _logger.info(f"[_replace_broken_signature] Ищем разбитую сигнатуру: {signature}")
            
            # Простой подход - ищем внутренний текст сигнатуры без фигурных скобок
            inner_text = signature.strip('{}')
            _logger.info(f"[_replace_broken_signature] Внутренний текст: {inner_text}")
            
            if inner_text in xml_content:
                _logger.info(f"[_replace_broken_signature] Найден внутренний текст в XML")
                # Заменяем внутренний текст на значение, но только внутри тегов <w:t>
                import re
                # Ищем паттерн: <w:t>...inner_text...</w:t> и заменяем только содержимое
                pattern = r'(<w:t[^>]*>)([^<]*' + re.escape(inner_text) + r'[^<]*)(<\/w:t>)'
                
                def replace_in_tag(match):
                    start_tag = match.group(1)
                    content = match.group(2)
                    end_tag = match.group(3)
                    # Используем центральную функцию экранирования
                    escaped_value = escape_xml_func(value)
                    new_content = content.replace(inner_text, escaped_value)
                    return start_tag + new_content + end_tag
                
                if re.search(pattern, xml_content):
                    xml_content = re.sub(pattern, replace_in_tag, xml_content)
                    _logger.info(f"[_replace_broken_signature] Замена выполнена через regex паттерн")
                    return xml_content
                else:
                    # Если паттерн не найден, попробуем простую замену
                    escaped_value = escape_xml_func(value)
                    xml_content = xml_content.replace(inner_text, escaped_value)
                    _logger.info(f"[_replace_broken_signature] Замена выполнена простым методом с экранированием")
                    return xml_content
            
            # Продвинутый поиск разбитых сигнатур
            # Ищем фрагменты сигнатуры в XML, учитывая что они могут быть разбиты
            _logger.info(f"[_replace_broken_signature] Ищем фрагменты сигнатуры...")
            
            # Создаем regex для поиска разбитой сигнатуры
            # Например, для "номер_контрактка" ищем "номер.*контрактка" с учетом XML тегов
            signature_parts = inner_text.split('_')
            if len(signature_parts) > 1:
                # Создаем паттерн, который учитывает возможные XML теги между частями
                pattern_parts = []
                for i, part in enumerate(signature_parts):
                    if part:  # Пропускаем пустые части
                        escaped_part = re.escape(part)
                        if i == 0:
                            # Первая часть может быть в отдельном теге
                            pattern_parts.append(f'(<w:t[^>]*>[^<]*?{escaped_part}[^<]*?</w:t>)')
                        else:
                            # Последующие части могут быть в других тегах, с подчеркиванием или без
                            pattern_parts.append(f'((?:<w:t[^>]*>[^<]*?_?{escaped_part}[^<]*?</w:t>)|(?:[^<]*?_?{escaped_part}[^<]*?))')
                
                if len(pattern_parts) >= 2:
                    # Объединяем части с возможными XML тегами между ними
                    full_pattern = '.*?'.join(pattern_parts)
                    _logger.info(f"[_replace_broken_signature] Паттерн для поиска: {full_pattern[:100]}...")
                    
                    match = re.search(full_pattern, xml_content, re.DOTALL)
                    if match:
                        _logger.info(f"[_replace_broken_signature] Найдена разбитая сигнатура!")
                        # Заменяем найденную область на значение
                        matched_text = match.group(0)
                        _logger.info(f"[_replace_broken_signature] Найденный текст: {matched_text[:100]}...")
                        
                        # Простая замена всего найденного блока на значение в теге <w:t>
                        escaped_value = escape_xml_func(value)
                        replacement = f'<w:t>{escaped_value}</w:t>'
                        xml_content = xml_content.replace(matched_text, replacement)
                        _logger.info(f"[_replace_broken_signature] Замена разбитой сигнатуры выполнена")
                        _logger.info(f"🔧 [ПОДИТОГ_ТЕКСТ] Экранированное значение: '{escaped_value}'")
                        return xml_content
            
            # Если ничего не найдено, попробуем поиск по частям
            parts = inner_text.split('_')
            if len(parts) > 1:
                _logger.info(f"[_replace_broken_signature] Ищем части сигнатуры: {parts}")
                
                # Проверяем, есть ли все части в документе
                all_parts_found = all(part in xml_content for part in parts if part)
                if all_parts_found:
                    _logger.info(f"[_replace_broken_signature] Все части найдены, выполняем замену")
                    # Заменяем каждую часть последовательно
                    temp_placeholder = f"__TEMP_REPLACEMENT_{hash(signature)}__"
                    
                    # Сначала заменяем первую часть на временный placeholder
                    if parts[0]:
                        xml_content = xml_content.replace(parts[0], temp_placeholder, 1)
                    
                    # Затем удаляем остальные части
                    for part in parts[1:]:
                        if part:
                            xml_content = xml_content.replace('_' + part, '', 1)
                    
                    # Заменяем placeholder на итоговое значение
                    escaped_value = escape_xml_func(value)
                    xml_content = xml_content.replace(temp_placeholder, escaped_value)
                    return xml_content
            
            _logger.info(f"[_replace_broken_signature] Не удалось найти сигнатуру: {signature}")
            return xml_content
            
        except Exception as e:
            _logger.error(f"[_replace_broken_signature] Ошибка при замене сигнатуры {signature}: {e}")
            return xml_content
    
    def _process_statement_docx_template(self, docx_path, template_data):
        """Обрабатывает DOCX шаблон заявления, заполняя таблицы"""
        import tempfile
        import os
        from zipfile import ZipFile
        
        try:
            _logger.info(f"[_process_statement_docx_template] Начинаем обработку шаблона заявления: {docx_path}")
            
            # Создаем временную папку для распаковки
            with tempfile.TemporaryDirectory() as temp_dir:
                # Распаковываем DOCX
                with ZipFile(docx_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Обрабатываем document.xml
                document_path = os.path.join(temp_dir, 'word', 'document.xml')
                if os.path.exists(document_path):
                    # Читаем содержимое XML
                    with open(document_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    _logger.info("=== ОТЛАДКА ОБРАБОТКИ ЗАЯВЛЕНИЯ ===")
                    _logger.info(f"Данные для замены: {template_data}")
                    _logger.info(f"Размер XML содержимого: {len(content)} символов")
                    
                    # Парсим XML
                    root = ET.fromstring(content)
                    
                    # Ищем таблицы
                    tables = root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl')
                    _logger.info(f"Найдено таблиц: {len(tables)}")
                    
                    total_replacements = 0
                    
                    if tables:
                        # Обрабатываем первую таблицу (предполагаем что заявление в первой таблице)
                        table = tables[0]
                        rows = table.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr')
                        _logger.info(f"Строк в таблице: {len(rows)}")
                        
                        for row_idx, row in enumerate(rows):
                            cells = row.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc')
                            
                            if len(cells) >= 2:  # Должно быть минимум 2 колонки
                                # Первая ячейка - название поля
                                left_cell = cells[0]
                                right_cell = cells[1]
                                
                                # Извлекаем текст из левой ячейки
                                left_text = self._extract_cell_text(left_cell)
                                right_text = self._extract_cell_text(right_cell)
                                
                                _logger.info(f"Строка {row_idx + 1}: '{left_text}' | '{right_text}'")
                                
                                # Пропускаем пустые строки и заголовки
                                if not left_text or left_text.lower() in ['заполняется клиентом', '']:
                                    continue
                                
                                # Ищем соответствующее значение в template_data
                                value = self._find_matching_value(left_text, template_data)
                                
                                if value is not None and str(value).strip():
                                    # Заполняем правую ячейку
                                    self._fill_cell_with_value(right_cell, value)
                                    total_replacements += 1
                                    _logger.info(f"✅ Заполнено поле '{left_text}' значением: '{value}'")
                                else:
                                    _logger.info(f"⚠️  Не найдено значение для поля: '{left_text}'")
                    
                    _logger.info(f"=== ИТОГИ ОБРАБОТКИ ЗАЯВЛЕНИЯ ===")
                    _logger.info(f"Всего выполнено замен: {total_replacements}")
                    
                    # Конвертируем обратно в строку
                    content = ET.tostring(root, encoding='unicode', method='xml')
                    
                    # Сохраняем изменения
                    with open(document_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Создаем результирующий DOCX файл
                    result_path = os.path.join(temp_dir, 'result.docx')
                    with ZipFile(result_path, 'w') as zip_ref:
                        for root_dir, dirs, files in os.walk(temp_dir):
                            for file in files:
                                if file != 'result.docx':
                                    file_path = os.path.join(root_dir, file)
                                    arcname = os.path.relpath(file_path, temp_dir)
                                    zip_ref.write(file_path, arcname)
                    
                    # Читаем результат
                    with open(result_path, 'rb') as f:
                        return f.read()
                        
        except Exception as e:
            _logger.error(f"[_process_statement_docx_template] Ошибка обработки DOCX заявления: {e}")
            import traceback
            _logger.error(f"[_process_statement_docx_template] Traceback: {traceback.format_exc()}")
            return None
    
    def _extract_cell_text(self, cell):
        """Извлекает текст из ячейки таблицы"""
        texts = []
        for t in cell.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
            if t.text:
                texts.append(t.text)
        return ''.join(texts).strip()
    
    def _find_matching_value(self, field_name, template_data):
        """Находит соответствующее значение для поля в template_data"""
        # Очищаем поле от звездочек и лишних символов для поиска
        field_name_clean = field_name.replace('*', '').strip()
        field_name_lower = field_name_clean.lower()
        
        _logger.info(f"[ПОИСК ЗНАЧЕНИЯ] Исходное поле: '{field_name}' -> очищенное: '{field_name_clean}'")
        
        # Расширенный маппинг полей из шаблона к ключам в template_data
        field_mapping = {
            # VALUE DATE - дата платежа
            'value date дата платежа': 'VALUE DATE*',
            'value date': 'VALUE DATE*',
            'дата платежа': 'VALUE DATE*',
            
            # AMOUNT - сумма
            'amount сумма': 'AMOUNT',
            'amount': 'AMOUNT',
            'сумма': 'AMOUNT',
            
            # CURRENCY - валюта  
            'currency валюта': 'CURRENCY',
            'currency': 'CURRENCY',
            'валюта': 'CURRENCY',
            
            # BILL TO - плательщик
            'bill to': 'BILL TO',
            
            # BENEFICIARY - получатель
            'beneficiary получатель': 'BENEFICIARY',
            'beneficiary': 'BENEFICIARY',
            'получатель': 'Beneficiary',
            
            # BENEFICIARY COUNTRY - страна получателя
            'beneficiary countryстрана получателя': 'Beneficiary COUNTRY',
            'beneficiary country': 'Beneficiary COUNTRY',
            'страна получателя': 'Beneficiary COUNTRY',
            
            # BENEFICIARY ADDRESS - адрес получателя
            'beneficiary address адрес получателя (город просьба указать)': 'Beneficiary address',
            'beneficiary address': 'Beneficiary address',
            'адрес получателя': 'Beneficiary address',
            
            # ACCOUNT - номер счета
            'account номер счета или iban код': 'ACCOUNT *',
            'account': 'ACCOUNT *',
            'номер счета': 'ACCOUNT *',
            'iban код': 'ACCOUNT *',
            
            # BENEF.BANK - банк получателя
            'benef.bank банк получателя': 'BENEF.BANK *',
            'benef.bank': 'BENEF.BANK *',
            'банк получателя': 'BENEF.BANK *',
            
            # ADDRESS - адрес банка получателя
            'addressадрес банка получателя(страну и город просьба указать)': 'ADDRESS*',
            'address': 'ADDRESS*',
            'адрес банка получателя': 'ADDRESS*',
            
            # SWIFT - свифт банка получателя
            'swift cвифт банка получателя': 'SWIFT *',
            'swift': 'SWIFT *',
            'свифт банка получателя': 'SWIFT *',
            'cвифт банка получателя': 'SWIFT *',
            
            # PAYMENT DETAILS - назначение платежа
            'payment details назначение платежа(обязательно указать категорию товара!)': 'PAYMENT DETAILS *',
            'payment details': 'PAYMENT DETAILS *',
            'назначение платежа': 'PAYMENT DETAILS *'
        }
        
        # Сначала ищем точное совпадение по полному тексту
        if field_name_lower in field_mapping:
            template_key = field_mapping[field_name_lower]
            if template_key in template_data:
                _logger.info(f"[ПОИСК ЗНАЧЕНИЯ] ✅ Точное совпадение: '{field_name_lower}' -> '{template_key}' = '{template_data[template_key]}'")
                return template_data[template_key]
        
        # Потом ищем частичное совпадение с приоритетом для более длинных ключей
        # Сортируем ключи по длине (сначала длинные, потом короткие)
        sorted_mapping = sorted(field_mapping.items(), key=lambda x: len(x[0]), reverse=True)
        
        for key_pattern, template_key in sorted_mapping:
            # Проверяем содержит ли поле ключевые слова из паттерна
            if self._fields_match(field_name_lower, key_pattern):
                if template_key in template_data:
                    _logger.info(f"[ПОИСК ЗНАЧЕНИЯ] ✅ Частичное совпадение: '{field_name_lower}' ~ '{key_pattern}' -> '{template_key}' = '{template_data[template_key]}'")
                    return template_data[template_key]
        
        # Если не нашли в маппинге, пробуем прямое сравнение с ключами template_data
        for template_key, value in template_data.items():
            template_key_clean = template_key.replace('*', '').strip().lower()
            if self._fields_match(field_name_lower, template_key_clean):
                _logger.info(f"[ПОИСК ЗНАЧЕНИЯ] ✅ Прямое совпадение: '{field_name_lower}' ~ '{template_key_clean}' = '{value}'")
                return value
        
        _logger.info(f"[ПОИСК ЗНАЧЕНИЯ] ❌ Не найдено значение для поля: '{field_name}'")
        return None
    
    def _fields_match(self, field1, field2):
        """Проверяет совпадение двух полей по ключевым словам с учетом порядка и контекста"""
        field1_lower = field1.lower().strip()
        field2_lower = field2.lower().strip()
        
        # Сначала проверяем точное совпадение
        if field1_lower == field2_lower:
            return True
        
        # Разбиваем на слова и убираем короткие слова
        words1 = [w for w in field1_lower.split() if len(w) > 2]
        words2 = [w for w in field2_lower.split() if len(w) > 2]
        
        if not words1 or not words2:
            return False
        
        # Специальная логика для избежания ложных совпадений
        # Если один из паттернов содержит "country", а другой нет - не совпадают
        has_country1 = any('country' in w or 'страна' in w for w in words1)
        has_country2 = any('country' in w or 'страна' in w for w in words2)
        
        if has_country1 != has_country2:
            return False
        
        # Если один из паттернов содержит "address", а другой нет - не совпадают  
        has_address1 = any('address' in w or 'адрес' in w for w in words1)
        has_address2 = any('address' in w or 'адрес' in w for w in words2)
        
        if has_address1 != has_address2:
            return False
        
        # Для точного совпадения нужно чтобы все значимые слова из более короткого поля 
        # присутствовали в более длинном поле
        shorter_words = words1 if len(words1) <= len(words2) else words2
        longer_words = words2 if len(words1) <= len(words2) else words1
        
        # Проверяем что все слова из короткого поля есть в длинном
        matches = 0
        for word in shorter_words:
            if word in longer_words:
                matches += 1
        
        # Требуем совпадения всех ключевых слов из короткого поля
        return matches == len(shorter_words)
    
    def _fill_cell_with_value(self, cell, value):
        """Заполняет ячейку таблицы значением"""
        
        # Очищаем существующий текст
        for t in cell.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
            t.text = ''
        
        # Ищем первый текстовый элемент или создаем новый
        text_elements = cell.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
        if text_elements:
            text_elements[0].text = str(value)
        else:
            # Создаем новую структуру для текста
            paragraph = cell.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
            if paragraph is not None:
                run = ET.SubElement(paragraph, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
                text_elem = ET.SubElement(run, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                text_elem.text = str(value)
 