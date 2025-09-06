# -*- coding: utf-8 -*-
import logging
import requests
import xml.etree.ElementTree as ET
from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class ZayavkaMethods(models.Model):
    _inherit = 'amanat.zayavka'

    def _duplicate_attachments_to_output(self):
        """
        Дублирует файлы из zayavka_attachments в zayavka_output_attachments
        Для One2many поля создаем копии attachment'ов
        ИСКЛЮЧАЕТ договоры контрагента из дублирования
        """
        for record in self:
            if record.zayavka_attachments:
                # Получаем имена файлов, которые уже есть в zayavka_output_attachments
                existing_names = set(record.zayavka_output_attachments.mapped('name'))
                
                # Получаем ID договоров контрагента, чтобы исключить их из дублирования
                contract_attachment_ids = set()
                if record.contragent_contract_attachments:
                    contract_attachment_ids = set(record.contragent_contract_attachments.ids)
                    _logger.info(f"Заявка {record.id}: исключаем из дублирования {len(contract_attachment_ids)} договоров контрагента")
                
                # Получаем файлы из zayavka_attachments, которых еще нет в zayavka_output_attachments
                # И которые НЕ являются договорами контрагента
                new_attachments = record.zayavka_attachments.filtered(
                    lambda att: att.name not in existing_names and att.id not in contract_attachment_ids
                )
                
                if new_attachments:
                    # Создаем копии attachment'ов для One2many поля
                    for attachment in new_attachments:
                        self.env['ir.attachment'].sudo().create({
                            'name': attachment.name,
                            'datas': attachment.datas,
                            'res_model': 'amanat.zayavka',
                            'res_id': record.id,
                            'res_field': 'zayavka_output_attachments',
                            'mimetype': attachment.mimetype,
                            'description': attachment.description or f'Копия из Заявка Вход: {attachment.name}',
                        })
                    _logger.info(f"Заявка {record.id}: создано {len(new_attachments)} копий файлов в zayavka_output_attachments (исключены договоры контрагента)")
                elif contract_attachment_ids:
                    _logger.info(f"Заявка {record.id}: дублирование пропущено - все файлы являются договорами контрагента или уже существуют")

    def write(self, vals):
        trigger = vals.get('fin_entry_check', False)
        trigger2 = vals.get('for_khalida_temp', False)
        send_to_reconciliation = vals.get('send_to_reconciliation', False)

        old_values = {}
        if 'extract_delivery_ids' in vals:
            for rec in self:
                old_values[rec.id] = rec.extract_delivery_ids.ids.copy()

        res = super().write(vals)  # <-- Исправлено!

        if 'rate_field' in vals:
            for rec in self:
                rec.status = '3'
                rec.rate_fixation_date = fields.Date.today()

        if 'extract_delivery_ids' in vals:
            _logger.info(f"Обнаружено изменение extract_delivery_ids в vals: {vals.get('extract_delivery_ids')}")
            for rec in self:
                old_ids = set(old_values.get(rec.id, []))
                new_ids = set(rec.extract_delivery_ids.ids)
                if old_ids != new_ids:
                    _logger.info(f"Заявка {rec.zayavka_num}: запуск автоматизаций при изменении выписок разнос")
                    rec._on_extract_delivery_ids_changed(old_ids, new_ids)
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
                
                if files_added:
                    _logger.info(f"Заявка {rec.id}: файлы акт-отчетов добавлены")
                
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
                rec._duplicate_attachments_to_output()
        
        if 'payment_date' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'payment_date' для заявки {rec.id}")
                rec.status = '6'

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
        
        if 'assignment_individual_attachments' in vals:
            for rec in self:
                rec.analyze_assignment_individual_with_yandex_gpt()

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
    def create(self, vals_list):
        # Обрабатываем как список, так и одиночные значения для совместимости
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        
        # Инициализируем переменные для триггеров
        trigger = False
        trigger2 = False
        send_to_reconciliation = False
        
        for vals in vals_list:
            range_id = vals.get('range_id')
            if not range_id:
                range_rec = self.env['amanat.ranges'].browse(1)
                if range_rec.exists():
                    vals['range_id'] = range_rec.id
                else:
                    _logger.warning('В таблице "Диапазон" не найдена запись с ID = 1.')

            # Сохраняем триггеры из последней записи (для совместимости со старым кодом)
            trigger = vals.get('fin_entry_check', False) or trigger
            trigger2 = vals.get('for_khalida_temp', False) or trigger2
            send_to_reconciliation = vals.get('send_to_reconciliation', False) or send_to_reconciliation
        
        res = super().create(vals_list)
        
        # Для работы с одиночными записями берем первый vals
        vals = vals_list[0] if vals_list else {}

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
            res._duplicate_attachments_to_output()

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

        if vals.get('assignment_individual_attachments'):
            res.analyze_assignment_individual_with_yandex_gpt()

        if vals.get('payment_date'):
            _logger.info(f"Изменено поле 'payment_date' для заявки {res.id}")
            res.status = '6'
        
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
        # Используем savepoint для изоляции операции создания
        with self.env.cr.savepoint():
            try:
                money = self.env['amanat.money'].create(vals)
                _logger.info(
                    f"Создан контейнер (money): partner={vals.get('partner_id')}, amount={vals.get('amount')}, currency={vals.get('currency')}, состояние={vals.get('state')}, ордер={vals.get('order_id')}"
                )
                return money
            except Exception as e:
                if "mail_followers" in str(e) and "duplicate key" in str(e):
                    _logger.warning(f"Проблема с подписчиками при создании money, создаем без подписчиков: {e}")
                    # Создаем в новом savepoint без подписчиков
                    with self.env.cr.savepoint():
                        money = self.env['amanat.money'].with_context(
                            mail_create_nosubscribe=True,
                            mail_create_nolog=True,
                            tracking_disable=True
                        ).create(vals)
                        _logger.info(
                            f"Создан контейнер (money) без подписчиков: partner={vals.get('partner_id')}, amount={vals.get('amount')}, currency={vals.get('currency')}, состояние={vals.get('state')}, ордер={vals.get('order_id')}"
                        )
                        return money
                else:
                    raise

    def _create_reconciliation(self, vals):
        # Используем savepoint для изоляции операции создания
        with self.env.cr.savepoint():
            try:
                reconciliation = self.env['amanat.reconciliation'].create(vals)
                _logger.info(f"Создана сверка: {reconciliation.id}, сумма={reconciliation.sum}, валюта={reconciliation.currency}")
                return reconciliation
            except Exception as e:
                if "mail_followers" in str(e) and "duplicate key" in str(e):
                    _logger.warning(f"Проблема с подписчиками при создании reconciliation, создаем без подписчиков: {e}")
                    # Создаем в новом savepoint без подписчиков
                    with self.env.cr.savepoint():
                        reconciliation = self.env['amanat.reconciliation'].with_context(
                            mail_create_nosubscribe=True,
                            mail_create_nolog=True,
                            tracking_disable=True
                        ).create(vals)
                        _logger.info(f"Создана сверка без подписчиков: {reconciliation.id}, сумма={reconciliation.sum}, валюта={reconciliation.currency}")
                        return reconciliation
                else:
                    raise


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
        """Генерация документа заявления по шаблону с улучшенной обработкой"""
        try:
            _logger.info(f"[ЗАЯВЛЕНИЕ] Начинаем генерацию заявления для записи ID {self.id}")
            
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
            
            # УДАЛЯЕМ СТАРЫЕ ФАЙЛЫ ЗАЯВЛЕНИЯ ПЕРЕД СОЗДАНИЕМ НОВЫХ
            self._remove_existing_statement_files()
            
            # ДОПОЛНИТЕЛЬНАЯ ОПЦИЯ: Удалить ВСЕ файлы из заявка_выход (раскомментируйте если нужно)
            # self._remove_all_output_files()
            
            # Подготавливаем данные для подстановки
            template_data = self._prepare_statement_template_data()
            
            # Генерируем документ используя надежный метод docxtpl
            generated_file = self._generate_statement_document_safe(template, template_data)
            
            if generated_file:
                # Создаем attachment
                attachment = self.env['ir.attachment'].sudo().create({
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
                
                _logger.info(f"[ЗАЯВЛЕНИЕ] ✅ Документ успешно сгенерирован: {attachment.name}")
                
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
            _logger.error(f"[ЗАЯВЛЕНИЕ] ❌ Ошибка при генерации документа заявления: {str(e)}")
            import traceback
            _logger.error(f"[ЗАЯВЛЕНИЕ] Traceback: {traceback.format_exc()}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка',
                    'message': f'Произошла ошибка при генерации документа: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def _remove_existing_statement_files(self):
        """Удаляет ВСЕ существующие файлы заявления из заявка_выход (независимо от способа загрузки)"""
        try:
            # Ищем ВСЕ файлы заявления в zayavka_output_attachments по различным критериям
            search_patterns = [
                ('name', 'ilike', 'заявление%'),      # Заявление*
                ('name', 'ilike', '%заявление%'),     # *заявление*
                ('name', 'ilike', 'statement%'),      # statement*
                ('name', 'ilike', '%statement%'),     # *statement*
                ('name', 'ilike', 'application%'),    # application*
                ('name', 'ilike', '%application%'),   # *application*
            ]
            
            all_statements = self.env['ir.attachment'].sudo()
            
            # Собираем все файлы по всем паттернам
            for pattern in search_patterns:
                statements = self.env['ir.attachment'].sudo().search([
                    ('res_model', '=', self._name),
                    ('res_id', '=', self.id),
                    ('res_field', '=', 'zayavka_output_attachments'),
                    pattern
                ])
                all_statements |= statements
            
            # Дополнительно ищем по расширению файла (docx, doc, pdf)
            doc_extensions = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('res_field', '=', 'zayavka_output_attachments'),
                '|', '|',
                ('name', 'ilike', '%.docx'),
                ('name', 'ilike', '%.doc'),
                ('name', 'ilike', '%.pdf')
            ])
            
            # Фильтруем только те, которые могут быть заявлениями
            for doc in doc_extensions:
                doc_name_lower = doc.name.lower()
                # Проверяем, содержит ли имя файла ключевые слова заявления
                if any(keyword in doc_name_lower for keyword in [
                    'заявл', 'statement', 'application', 'заяв', 'зая'
                ]):
                    all_statements |= doc
            
            # Удаляем дубликаты
            all_statements = all_statements.sudo()  # Используем sudo для гарантированного доступа
            
            if all_statements:
                _logger.info(f"[ЗАЯВЛЕНИЕ] 🗑️ Найдено {len(all_statements)} файлов заявления для удаления:")
                for attachment in all_statements:
                    _logger.info(f"[ЗАЯВЛЕНИЕ]   - Удаляем: {attachment.name} (ID: {attachment.id})")
                
                # Удаляем все найденные файлы
                all_statements.unlink()
                _logger.info(f"[ЗАЯВЛЕНИЕ] ✅ Успешно удалено {len(all_statements)} файлов заявления")
            else:
                _logger.info("[ЗАЯВЛЕНИЕ] 📝 Файлов заявления для удаления не найдено")
                
        except Exception as e:
            _logger.error(f"[ЗАЯВЛЕНИЕ] ❌ Ошибка при удалении существующих файлов заявления: {e}")
            import traceback
            _logger.error(f"[ЗАЯВЛЕНИЕ] Traceback: {traceback.format_exc()}")
    
    def _remove_all_output_files(self):
        """Удаляет ВСЕ файлы из заявка_выход (агрессивная очистка)"""
        try:
            # Ищем ВСЕ файлы в zayavka_output_attachments
            all_output_files = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('res_field', '=', 'zayavka_output_attachments')
            ]).sudo()
            
            if all_output_files:
                _logger.info(f"[ЗАЯВЛЕНИЕ] 🗑️ АГРЕССИВНАЯ ОЧИСТКА: Удаляем ВСЕ {len(all_output_files)} файлов из заявка_выход:")
                for attachment in all_output_files:
                    _logger.info(f"[ЗАЯВЛЕНИЕ]   - Удаляем: {attachment.name} (ID: {attachment.id})")
                
                all_output_files.unlink()
                _logger.info(f"[ЗАЯВЛЕНИЕ] ✅ Агрессивная очистка завершена: удалено {len(all_output_files)} файлов")
            else:
                _logger.info("[ЗАЯВЛЕНИЕ] 📝 Файлов для агрессивной очистки не найдено")
                
        except Exception as e:
            _logger.error(f"[ЗАЯВЛЕНИЕ] ❌ Ошибка при агрессивной очистке файлов: {e}")
            import traceback
            _logger.error(f"[ЗАЯВЛЕНИЕ] Traceback: {traceback.format_exc()}")
    
    def _generate_statement_document_safe(self, template, template_data):
        """Безопасная генерация документа заявления используя только docxtpl"""
        import base64
        import tempfile
        import os
        
        try:
            _logger.info("[ЗАЯВЛЕНИЕ] 🔧 Используем безопасный метод генерации с docxtpl")
            
            # Проверяем наличие docxtpl
            try:
                from docxtpl import DocxTemplate  # type: ignore
            except ImportError:
                _logger.error("[ЗАЯВЛЕНИЕ] ❌ docxtpl не установлен! Установите: pip install docxtpl")
                return None
            
            # Декодируем файл шаблона
            template_bytes = base64.b64decode(template.template_file)
            
            # Создаем временный файл для работы
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(template_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Создаем объект шаблона
                doc = DocxTemplate(temp_file_path)
                
                _logger.info(f"[ЗАЯВЛЕНИЕ] 📝 Обрабатываем шаблон с {len(template_data)} переменными")
                
                # ОТЛАДКА: Проверяем, какие переменные найдены в шаблоне
                try:
                    # Получаем список переменных из шаблона
                    template_vars = doc.get_undeclared_template_variables()
                    _logger.info(f"[ЗАЯВЛЕНИЕ] 🔍 Переменные, найденные в шаблоне: {template_vars}")
                    
                    # Проверяем совпадения
                    our_vars = set(template_data.keys())
                    template_vars_set = set(template_vars)
                    
                    matches = our_vars.intersection(template_vars_set)
                    missing_in_template = our_vars - template_vars_set
                    missing_in_data = template_vars_set - our_vars
                    
                    _logger.info(f"[ЗАЯВЛЕНИЕ] ✅ Совпадающие переменные ({len(matches)}): {matches}")
                    _logger.info(f"[ЗАЯВЛЕНИЕ] ❌ Наши переменные, отсутствующие в шаблоне ({len(missing_in_template)}): {missing_in_template}")
                    _logger.info(f"[ЗАЯВЛЕНИЕ] ⚠️ Переменные шаблона, для которых нет данных ({len(missing_in_data)}): {missing_in_data}")
                    
                except Exception as debug_e:
                    _logger.warning(f"[ЗАЯВЛЕНИЕ] Не удалось получить переменные шаблона: {debug_e}")
                
                # Рендерим шаблон с данными
                doc.render(template_data)
                
                # Сохраняем результат
                with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as result_file:
                    result_file_path = result_file.name
                
                try:
                    # Сохраняем документ
                    doc.save(result_file_path)
                    
                    # Читаем байты
                    with open(result_file_path, 'rb') as f:
                        result_bytes = f.read()
                    
                    _logger.info("[ЗАЯВЛЕНИЕ] ✅ Документ успешно сгенерирован с docxtpl")
                    return base64.b64encode(result_bytes).decode('utf-8')
                    
                finally:
                    # Удаляем временный файл результата
                    try:
                        os.unlink(result_file_path)
                    except Exception:
                        pass
                        
            finally:
                # Удаляем временный файл шаблона
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass
                    
        except Exception as e:
            _logger.error(f"[ЗАЯВЛЕНИЕ] ❌ Ошибка при безопасной генерации документа: {str(e)}")
            import traceback
            _logger.error(f"[ЗАЯВЛЕНИЕ] Traceback: {traceback.format_exc()}")
            return None
    
    def _is_russian_text(self, text):
        """Проверяет, содержит ли текст русские символы"""
        if not text:
            return False
        
        import re
        # Проверяем наличие кириллических символов
        return bool(re.search(r'[а-яё]', text.lower()))
    
    def test_yandex_gpt_translation(self, test_text="Тестовая страна"):
        """Тестовый метод для проверки работы YandexGPT"""
        _logger.info(f"[ТЕСТ] 🧪 Тестируем перевод YandexGPT для: '{test_text}'")
        
        try:
            from odoo.addons.amanat.models.zayavka.automations.ygpt_analyse import _get_yandex_gpt_config
            cfg = _get_yandex_gpt_config(self.env, "zayavka")
            
            _logger.info(f"[ТЕСТ] Конфигурация: api_key={'есть' if cfg['api_key'] else 'НЕТ'}, folder_id={'есть' if cfg['folder_id'] else 'НЕТ'}")
            
            if not cfg['api_key'] or not cfg['folder_id']:
                return {
                    'success': False,
                    'error': 'API ключ или Folder ID не настроены',
                    'config': {
                        'api_key_present': bool(cfg['api_key']),
                        'folder_id_present': bool(cfg['folder_id'])
                    }
                }
            
            result = self._translate_text_via_yandex_gpt(test_text)
            
            return {
                'success': True,
                'original': test_text,
                'translated': result,
                'config': {
                    'api_key_present': True,
                    'folder_id_present': True
                }
            }
            
        except Exception as e:
            _logger.error(f"[ТЕСТ] Ошибка при тестировании YandexGPT: {e}")
            return {
                'success': False,
                'error': str(e),
                'original': test_text
            }

    def _get_country_translation_fallback(self, country_ru):
        """Fallback метод для перевода стран когда поле eng_country_name не заполнено"""
        # Проверяем, нужен ли перевод (если страна на русском языке)
        is_russian = self._is_russian_text(country_ru)
        _logger.info(f"[ЗАЯВЛЕНИЕ] 🔍 Анализ страны '{country_ru}': is_russian={is_russian}")
        
        if is_russian:
            _logger.info(f"[ЗАЯВЛЕНИЕ] 🌍 Переводим страну с русского: '{country_ru}'")
            country_en = self._translate_country_to_english(country_ru)
            if country_en and country_en != country_ru:
                _logger.info(f"[ЗАЯВЛЕНИЕ] ✅ Страна переведена: '{country_ru}' -> '{country_en}'")
                return country_en
            else:
                _logger.info(f"[ЗАЯВЛЕНИЕ] ⚠️ Перевод не удался, используем оригинал: '{country_ru}'")
                return country_ru
        else:
            # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: Возможно, это смешанный текст или нужен принудительный перевод
            _logger.info(f"[ЗАЯВЛЕНИЕ] 🔍 Страна распознана как НЕ русская: '{country_ru}'")
            
            # Проверим, есть ли эта страна в нашем словаре (принудительный перевод)
            country_en = self._translate_country_to_english(country_ru)
            if country_en and country_en != country_ru:
                _logger.info(f"[ЗАЯВЛЕНИЕ] 🔄 Принудительный перевод из словаря: '{country_ru}' -> '{country_en}'")
                return country_en
            else:
                _logger.info(f"[ЗАЯВЛЕНИЕ] 📝 Оставляем как есть: '{country_ru}'")
                return country_ru

    def _translate_country_to_english(self, country_ru):
        """Переводит название страны с русского на английский через Яндекс GPT"""
        try:
            # Сначала пробуем простой словарь для популярных стран
            country_mapping = {
                # Россия и варианты
                'россия': 'Russia',
                'российская федерация': 'Russia',
                'рф': 'Russia',
                'russia': 'Russia',
                
                # Китай и варианты
                'китай': 'China',
                'кнр': 'China',
                'china': 'China',
                'people\'s republic of china': 'China',
                
                # США и варианты
                'сша': 'USA',
                'соединенные штаты америки': 'USA',
                'соединённые штаты америки': 'USA',
                'америка': 'USA',
                'usa': 'USA',
                'united states': 'USA',
                'united states of america': 'USA',
                
                # Европа
                'германия': 'Germany',
                'germany': 'Germany',
                'франция': 'France',
                'france': 'France',
                'италия': 'Italy',
                'italy': 'Italy',
                'испания': 'Spain',
                'spain': 'Spain',
                'великобритания': 'United Kingdom',
                'англия': 'United Kingdom',
                'uk': 'United Kingdom',
                'united kingdom': 'United Kingdom',
                'britain': 'United Kingdom',
                
                # Азия
                'япония': 'Japan',
                'japan': 'Japan',
                'индия': 'India',
                'india': 'India',
                'южная корея': 'South Korea',
                'корея': 'South Korea',
                'south korea': 'South Korea',
                'korea': 'South Korea',
                'турция': 'Turkey',
                'turkey': 'Turkey',
                
                # Ближний Восток
                'египет': 'Egypt',
                'egypt': 'Egypt',
                'саудовская аравия': 'Saudi Arabia',
                'saudi arabia': 'Saudi Arabia',
                'оаэ': 'UAE',
                'объединенные арабские эмираты': 'UAE',
                'объединённые арабские эмираты': 'UAE',
                'uae': 'UAE',
                'united arab emirates': 'UAE',
                
                # Юго-Восточная Азия
                'таиланд': 'Thailand',
                'тайланд': 'Thailand',  # Альтернативное написание
                'thailand': 'Thailand',
                'вьетнам': 'Vietnam',
                'vietnam': 'Vietnam',
                'индонезия': 'Indonesia',
                'indonesia': 'Indonesia',
                'малайзия': 'Malaysia',
                'malaysia': 'Malaysia',
                'сингапур': 'Singapore',
                'singapore': 'Singapore',
                'филиппины': 'Philippines',
                'philippines': 'Philippines',
                
                # Америки
                'бразилия': 'Brazil',
                'brazil': 'Brazil',
                'канада': 'Canada',
                'canada': 'Canada',
                'мексика': 'Mexico',
                'mexico': 'Mexico',
                'аргентина': 'Argentina',
                'argentina': 'Argentina',
                
                # Океания
                'австралия': 'Australia',
                'australia': 'Australia',
                
                # СНГ
                'казахстан': 'Kazakhstan',
                'kazakhstan': 'Kazakhstan',
                'узбекистан': 'Uzbekistan',
                'uzbekistan': 'Uzbekistan',
                'беларусь': 'Belarus',
                'белоруссия': 'Belarus',
                'belarus': 'Belarus',
                'украина': 'Ukraine',
                'ukraine': 'Ukraine',
                
                # Восточная Европа
                'польша': 'Poland',
                'poland': 'Poland',
                'чехия': 'Czech Republic',
                'czech republic': 'Czech Republic',
                'венгрия': 'Hungary',
                'hungary': 'Hungary',
                'румыния': 'Romania',
                'romania': 'Romania',
                'болгария': 'Bulgaria',
                'bulgaria': 'Bulgaria',
                'сербия': 'Serbia',
                'serbia': 'Serbia',
                'хорватия': 'Croatia',
                'croatia': 'Croatia',
                'словения': 'Slovenia',
                'slovenia': 'Slovenia',
                'словакия': 'Slovakia',
                'slovakia': 'Slovakia',
                
                # Балтика и Скандинавия
                'литва': 'Lithuania',
                'lithuania': 'Lithuania',
                'латвия': 'Latvia',
                'latvia': 'Latvia',
                'эстония': 'Estonia',
                'estonia': 'Estonia',
                'финляндия': 'Finland',
                'finland': 'Finland',
                'швеция': 'Sweden',
                'sweden': 'Sweden',
                'норвегия': 'Norway',
                'norway': 'Norway',
                'дания': 'Denmark',
                'denmark': 'Denmark',
                
                # Западная Европа
                'нидерланды': 'Netherlands',
                'голландия': 'Netherlands',
                'netherlands': 'Netherlands',
                'holland': 'Netherlands',
                'бельгия': 'Belgium',
                'belgium': 'Belgium',
                'швейцария': 'Switzerland',
                'switzerland': 'Switzerland',
                'австрия': 'Austria',
                'austria': 'Austria',
                'португалия': 'Portugal',
                'portugal': 'Portugal',
                'греция': 'Greece',
                'greece': 'Greece',
                'кипр': 'Cyprus',
                'cyprus': 'Cyprus',
                'мальта': 'Malta',
                'malta': 'Malta',
                'ирландия': 'Ireland',
                'ireland': 'Ireland',
                'исландия': 'Iceland',
                'iceland': 'Iceland',
            }
            
            country_lower = country_ru.lower().strip()
            _logger.info(f"[ПЕРЕВОД СТРАНЫ] 🔍 Ищем в словаре: '{country_lower}' (исходный: '{country_ru}')")
            _logger.info(f"[ПЕРЕВОД СТРАНЫ] 📖 Размер словаря: {len(country_mapping)} стран")
            
            if country_lower in country_mapping:
                result = country_mapping[country_lower]
                _logger.info(f"[ПЕРЕВОД СТРАНЫ] 📚 ✅ Найдено в словаре: '{country_ru}' -> '{result}'")
                return result
            else:
                _logger.info(f"[ПЕРЕВОД СТРАНЫ] ❌ Не найдено в словаре: '{country_lower}'")
                # Покажем несколько похожих ключей для отладки
                similar_keys = [key for key in country_mapping.keys() if country_lower in key or key in country_lower]
                if similar_keys:
                    _logger.info(f"[ПЕРЕВОД СТРАНЫ] 🔍 Похожие ключи в словаре: {similar_keys[:5]}")
                else:
                    _logger.info(f"[ПЕРЕВОД СТРАНЫ] 🔍 Похожих ключей не найдено")
            
            # Если не найдено в словаре, используем Яндекс GPT
            _logger.info(f"[ПЕРЕВОД СТРАНЫ] 🤖 Используем Яндекс GPT для перевода: '{country_ru}'")
            
            prompt = f"""Переведи название страны на английский язык. Отвечай ТОЛЬКО названием страны на английском.

{country_ru} = """

            # Используем существующий метод для перевода через Яндекс GPT
            translated = self._translate_text_via_yandex_gpt(prompt)
            
            _logger.info(f"[ПЕРЕВОД СТРАНЫ] 🔍 Сырой ответ от Яндекс GPT: '{translated}'")
            
            if translated and translated.strip():
                # Очищаем результат от лишних символов
                result = translated.strip().replace('"', '').replace("'", "")
                
                # ПРОВЕРЯЕМ, НЕ ВЕРНУЛ ЛИ GPT ВЕСЬ ПРОМПТ
                if prompt in result or len(result) > 50:
                    _logger.warning(f"[ПЕРЕВОД СТРАНЫ] ⚠️ Яндекс GPT вернул промпт или слишком длинный ответ: '{result[:100]}...'")
                    # Пробуем извлечь только последнюю строку (возможный ответ)
                    lines = result.split('\n')
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line and len(last_line) < 30 and not self._is_russian_text(last_line):
                            _logger.info(f"[ПЕРЕВОД СТРАНЫ] 🔄 Извлекли ответ из последней строки: '{last_line}'")
                            return last_line
                
                # Проверяем, что результат не содержит русских символов и разумной длины
                if not self._is_russian_text(result) and len(result) < 30:
                    _logger.info(f"[ПЕРЕВОД СТРАНЫ] ✅ Яндекс GPT перевел: '{country_ru}' -> '{result}'")
                    return result
                else:
                    _logger.warning(f"[ПЕРЕВОД СТРАНЫ] ⚠️ Яндекс GPT вернул неподходящий текст: '{result[:50]}...'")
            
            # Если перевод не удался, возвращаем оригинал
            _logger.warning(f"[ПЕРЕВОД СТРАНЫ] ❌ Не удалось перевести '{country_ru}', используем оригинал")
            return country_ru
            
        except Exception as e:
            _logger.error(f"[ПЕРЕВОД СТРАНЫ] ❌ Ошибка при переводе страны '{country_ru}': {e}")
            return country_ru
    
    def _is_agent_allowed_for_individual_document(self):
        """Проверяет, разрешена ли генерация документа 'Индивидуал' для текущего агента"""
        if not self.agent_id or not self.agent_id.name:
            return False, "Агент не выбран"
        
        agent_name = str(self.agent_id.name).strip().lower()
        
        # Список разрешенных агентов с вариантами написания
        allowed_agents = [
            # СТЕЛЛАР
            ['стеллар', 'stellar', 'стелар', 'stelllar'],
            # ИНДО ТРЕЙД  
            ['индо трейд', 'indo trade', 'индотрейд', 'indo-trade', 'индо-трейд'],
            # ТДК
            ['тдк', 'tdk', 'т.д.к.', 't.d.k.', 'тдк.']
        ]
        
        # Проверяем точные совпадения и нечеткие
        for agent_group in allowed_agents:
            for variant in agent_group:
                # Точное совпадение
                if variant in agent_name:
                    _logger.info(f"✅ Агент '{self.agent_id.name}' разрешен для генерации (точное совпадение: '{variant}')")
                    return True, f"Разрешен (совпадение: {variant})"
                
                # Нечеткое совпадение (расстояние Левенштейна)
                similarity = self._calculate_similarity(agent_name, variant)
                if similarity > 0.8:  # 80% схожести
                    _logger.info(f"✅ Агент '{self.agent_id.name}' разрешен для генерации (нечеткое совпадение: '{variant}', схожесть: {similarity:.2f})")
                    return True, f"Разрешен (нечеткое совпадение: {variant}, {similarity:.0%})"
        
        _logger.warning(f"❌ Агент '{self.agent_id.name}' НЕ разрешен для генерации документа 'Индивидуал'")
        return False, f"Агент '{self.agent_id.name}' не входит в список разрешенных (СТЕЛЛАР, ИНДО ТРЕЙД, ТДК)"
    
    def _calculate_similarity(self, str1, str2):
        """Вычисляет схожесть строк (расстояние Левенштейна)"""
        if len(str1) < len(str2):
            return self._calculate_similarity(str2, str1)
        
        if len(str2) == 0:
            return 0.0
        
        previous_row = list(range(len(str2) + 1))
        for i, c1 in enumerate(str1):
            current_row = [i + 1]
            for j, c2 in enumerate(str2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
                # Возвращаем схожесть как долю от 0 до 1
        max_len = max(len(str1), len(str2))
        return 1.0 - (previous_row[-1] / max_len)
    
    def _compute_can_generate_individual(self):
        """Вычисляет, может ли текущий агент генерировать документ 'Индивидуал'"""
        for record in self:
            is_allowed, _ = record._is_agent_allowed_for_individual_document()
            record.can_generate_individual = is_allowed
    
    def action_generate_individual_document(self):
        """Генерация документа Индивидуал по шаблону"""
        try:
            # Проверяем, разрешен ли агент для генерации
            is_allowed, reason = self._is_agent_allowed_for_individual_document()
            if not is_allowed:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Доступ ограничен',
                        'message': f'Генерация документа "Индивидуал" доступна только для агентов: СТЕЛЛАР, ИНДО ТРЕЙД, ТДК.\n\n{reason}',
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            
            # Получаем формат из поля записи
            output_format = self.document_format or 'pdf'
            
            # Определяем какой шаблон использовать на основе галочки fixed_reward
            template_name = 'Индивидуал' if self.fixed_reward else 'Индивидуал Старый'
            
            _logger.info(f"=== ГЕНЕРАЦИЯ ДОКУМЕНТА ИНДИВИДУАЛ ДЛЯ ЗАЯВКИ ID {self.id} ===")
            _logger.info(f"Агент проверен: {reason}")
            _logger.info(f"Формат вывода: {output_format} (из поля document_format)")
            _logger.info(f"Фиксированное вознаграждение: {self.fixed_reward}")
            _logger.info(f"Выбранный шаблон: {template_name}")
            
            # Ищем шаблон на основе выбора пользователя
            template = self.env['template.library'].search([
                ('name', '=', template_name),
                ('template_type', '=', 'docx')
            ], limit=1)
            
            if not template:
                # Если шаблон "Индивидуал Старый" не найден, используем обычный "Индивидуал"
                if template_name == 'Индивидуал Старый':
                    _logger.warning(f"Шаблон '{template_name}' не найден, используем 'Индивидуал'")
                    template = self.env['template.library'].search([
                        ('name', '=', 'Индивидуал'),
                        ('template_type', '=', 'docx')
                    ], limit=1)
                    template_name = 'Индивидуал'  # Обновляем имя для корректного логирования
                
                if not template:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Ошибка',
                            'message': f'Шаблон "{template_name}" не найден в библиотеке шаблонов',
                            'type': 'danger',
                            'sticky': True,
                        }
                    }
            
            # Подготавливаем данные для подстановки
            template_data = self._prepare_individual_template_data()
            
            # Генерируем документ
            generated_file = self._generate_document_from_template(template, template_data)
            
            if generated_file:
                # Определяем имя файла и mimetype в зависимости от формата
                if output_format == 'pdf':
                    # Конвертируем в PDF с подписанием
                    pdf_file = self._convert_docx_to_pdf_base64(generated_file, sign_individual=True)
                    if pdf_file:
                        file_prefix = 'Индивидуал' if self.fixed_reward else 'Индивидуал_старый'
                        file_name = f'{file_prefix}_{self.zayavka_num or self.zayavka_id}.pdf'
                        file_data = pdf_file
                        mimetype = 'application/pdf'
                    else:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Ошибка',
                                'message': 'Не удалось конвертировать документ в PDF',
                                'type': 'danger',
                                'sticky': True,
                            }
                        }
                elif output_format == 'docx':
                    file_prefix = 'Индивидуал' if self.fixed_reward else 'Индивидуал_старый'
                    file_name = f'{file_prefix}_{self.zayavka_num or self.zayavka_id}.docx'
                    file_data = generated_file
                    mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                else:
                    # Fallback на PDF если формат неизвестен
                    pdf_file = self._convert_docx_to_pdf_base64(generated_file, sign_individual=True)
                    file_prefix = 'Индивидуал' if self.fixed_reward else 'Индивидуал_старый'
                    if pdf_file:
                        file_name = f'{file_prefix}_{self.zayavka_num or self.zayavka_id}.pdf'
                        file_data = pdf_file
                        mimetype = 'application/pdf'
                    else:
                        file_name = f'{file_prefix}_{self.zayavka_num or self.zayavka_id}.docx'
                        file_data = generated_file
                        mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                
                # Создаем attachment
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': file_name,
                    'type': 'binary',
                    'datas': file_data,
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': mimetype,
                })
                
                # Добавляем attachment к полю assignment_end_attachments
                self.assignment_end_attachments = [(4, attachment.id)]
                
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
            _logger.error(f"Ошибка при генерации документа Индивидуал: {str(e)}")
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
    
    def _prepare_individual_template_data(self):
        """Подготавливает данные для подстановки в шаблон Индивидуал"""
        from datetime import datetime
        
        # Русские и английские названия месяцев
        russian_months = {
            1: 'Января', 2: 'Февраля', 3: 'Марта', 4: 'Апреля',
            5: 'Мая', 6: 'Июня', 7: 'Июля', 8: 'Августа',
            9: 'Сентября', 10: 'Октября', 11: 'Ноября', 12: 'Декабря'
        }
        
        english_months = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        
        def format_russian_date(date_obj):
            """Форматирует дату в русском формате: "18" Августа 2025"""
            if not date_obj:
                return ""
            try:
                day = date_obj.day
                month = russian_months.get(date_obj.month, date_obj.strftime('%B'))
                year = date_obj.year
                return f'«{day}» {month} {year}'
            except (AttributeError, ValueError):
                return str(date_obj)
        
        def format_english_date(date_obj):
            """Форматирует дату в английском формате: August 18, 2025"""
            if not date_obj:
                return ""
            try:
                day = date_obj.day
                month = english_months.get(date_obj.month, date_obj.strftime('%B'))
                year = date_obj.year
                return f'{month} {day}, {year}'
            except (AttributeError, ValueError):
                return str(date_obj)
        
        def format_simple_date(date_obj):
            """Форматирует дату в простом формате: дд.мм.гггг"""
            if not date_obj:
                return ""
            try:
                return date_obj.strftime('%d.%m.%Y')
            except (AttributeError, ValueError):
                return str(date_obj)
        
        # Номер поручения
        instruction_number = self.instruction_number or ""

        # Агентский договор
        agency_agreement = self.agency_agreement or ""
        
        # Дата подписания агент-субагент (простой формат дд.мм.гггг)
        agent_contract_date_formatted = format_simple_date(self.agent_contract_date)
        
        # Дата подписания поручения (русский и английский форматы)
        instruction_signed_date_ru = format_russian_date(self.instruction_signed_date)
        instruction_signed_date_en = format_english_date(self.instruction_signed_date)
        
        # Агент (русский и английский)
        agent_name_ru = ""
        agent_name_en = ""
        if self.agent_id and self.agent_id.name:
            agent_name_ru = str(self.agent_id.name).strip()
            # Переводим через YandexGPT
            agent_name_en = self._translate_text_via_yandex_gpt(agent_name_ru)
        
        # Клиент (русский и английский)
        client_name_ru = ""
        client_name_en = ""
        if self.client_id and self.client_id.name:
            client_name_ru = str(self.client_id.name).strip()
            # Переводим через YandexGPT
            client_name_en = self._translate_text_via_yandex_gpt(client_name_ru)
        
        # Остальные поля
        exporter_importer_name = str(self.exporter_importer_name).strip() if self.exporter_importer_name else ""
        beneficiary_address = str(self.beneficiary_address).strip() if self.beneficiary_address else ""
        beneficiary_bank_name = str(self.beneficiary_bank_name).strip() if self.beneficiary_bank_name else ""
        bank_address = str(self.bank_address).strip() if self.bank_address else ""
        bank_swift = str(self.bank_swift).strip() if self.bank_swift else ""
        amount = f"{float(self.amount or 0):.2f}" if self.amount else "0.00"
        currency = str(self.currency).upper() if self.currency else ""
        rate = f"{float(self.rate_field or 0):.4f}" if self.rate_field else ""
        
        _logger.info("=== ДАННЫЕ ДЛЯ ШАБЛОНА ИНДИВИДУАЛ ===")
        _logger.info(f"Номер поручения: '{instruction_number}'")
        _logger.info(f"Дата агент-субагент: '{agent_contract_date_formatted}'")
        _logger.info(f"Дата поручения (RU): '{instruction_signed_date_ru}'")
        _logger.info(f"Дата поручения (EN): '{instruction_signed_date_en}'")
        _logger.info(f"Агент (RU): '{agent_name_ru}'")
        _logger.info(f"Агент (EN): '{agent_name_en}'")
        _logger.info(f"Клиент (RU): '{client_name_ru}'")
        _logger.info(f"Клиент (EN): '{client_name_en}'")
        
        # Создаем данные для docxtpl шаблона (формат {{переменная}})
        template_data = {
            # ✅ ОСНОВНЫЕ сигнатуры:
            'номер_п': instruction_number,
            'подписан_а_с': agent_contract_date_formatted,
            'наименование_покупателя_продавца': exporter_importer_name,
            'адрес_получателя': beneficiary_address,
            'банк_получателя': beneficiary_bank_name,
            'адрес_банка_получателя': bank_address,
            'swift_код': bank_swift,
            'подписано_п': instruction_signed_date_ru,
            'order_s': instruction_signed_date_en,
            'сумма': amount,
            'валюта': currency,
            'курс': rate,
            'агентский_д': agency_agreement,
            
            # ✅ ДОПОЛНИТЕЛЬНЫЕ сигнатуры:
            'агент': agent_name_ru,
            'agent': agent_name_en,
            'клиент': client_name_ru,
            'client': client_name_en,
            
            # ✅ НОВЫЕ сигнатуры для шаблона "Индивидуал старый":
            'получатель': exporter_importer_name,  # {{получатель}} - Наименование покупателя/продавца
            'расчетный_счет': self.iban_accc or "",  # {{расчетный_счет}} - IBAN/номер счета
            'swfit_код': bank_swift,  # {{swfit_код}} - указан в заявке (с опечаткой как в требованиях)
            'процент_вознагрождение': f"{float(self.hand_reward_percent or 0):.2f}%" if self.hand_reward_percent else "0.00%",  # {{процент_вознагрождение}} - указан в заявке
            'заявка_по_курсу_рублей': f"{float(self.application_amount_rub_contract or 0):.2f}" if self.application_amount_rub_contract else "0.00",  # {{заявка_по_курсу_рублей}} - указан в заявке
        }
        
        # КРИТИЧЕСКИ ВАЖНО: Убеждаемся что ВСЕ значения являются строками
        # docxtpl не может обрабатывать булевы значения, числа и None
        safe_template_data = {}
        for key, value in template_data.items():
            if value is None:
                safe_template_data[key] = ""
            elif isinstance(value, bool):
                safe_template_data[key] = "Да" if value else "Нет"
            elif isinstance(value, (int, float)):
                safe_template_data[key] = str(value)
            else:
                safe_template_data[key] = str(value)
        
        # Логируем все подготовленные данные для отладки
        _logger.info("=== ВСЕ ПОДГОТОВЛЕННЫЕ ДАННЫЕ ДЛЯ ШАБЛОНА ===")
        for key, value in safe_template_data.items():
            _logger.info(f"'{key}' -> '{value}' (длина: {len(str(value))}, тип: {type(value).__name__})")
        _logger.info("=== КОНЕЦ СПИСКА ДАННЫХ ===")
        
        return safe_template_data
    
    def _translate_text_via_yandex_gpt(self, text):
        """Переводит текст с русского на английский через YandexGPT"""
        if not text or not text.strip():
            return ""
        
        try:
            # Используем прямой вызов YandexGPT API для перевода
            try:
                from odoo.addons.amanat.models.zayavka.automations.ygpt_analyse import _get_yandex_gpt_config
                cfg = _get_yandex_gpt_config(self.env, "zayavka")
                _logger.info(f"[ПЕРЕВОД] Получена конфигурация YandexGPT: api_key={'***' if cfg['api_key'] else 'НЕТ'}, folder_id={'***' if cfg['folder_id'] else 'НЕТ'}")
            except ImportError as e:
                _logger.error(f"[ПЕРЕВОД] Не удалось импортировать _get_yandex_gpt_config: {e}")
                return text
            except Exception as e:
                _logger.error(f"[ПЕРЕВОД] Ошибка при получении конфигурации YandexGPT: {e}")
                return text
                
            if not cfg['api_key'] or not cfg['folder_id']:
                _logger.error(f"[ПЕРЕВОД] Не настроены API ключ и/или Folder ID. api_key: {'есть' if cfg['api_key'] else 'НЕТ'}, folder_id: {'есть' if cfg['folder_id'] else 'НЕТ'}")
                _logger.info("[ПЕРЕВОД] Для настройки YandexGPT перейдите в Настройки -> Технические -> Параметры -> Системные параметры и добавьте:")
                _logger.info("[ПЕРЕВОД] - amanat.ygpt.api_key = ваш_api_ключ")
                _logger.info("[ПЕРЕВОД] - amanat.ygpt.folder_id = ваш_folder_id")
                return text

            # Специальные случаи для известных сокращений
            special_translations = {
                'ТДК': 'TDK',
                'СТЕЛЛАР': 'STELLAR',
                'ООО': 'LLC',
                'АО': 'JSC',
                'ЗАО': 'CJSC',
                'ПАО': 'PJSC',
                'ИП': 'IE',  # Individual Entrepreneur
            }
            
            # Проверяем точные совпадения
            if text.strip() in special_translations:
                result = special_translations[text.strip()]
                _logger.info(f"[ПЕРЕВОД] Специальный перевод '{text}' -> '{result}'")
                return result

            # Простой и четкий промпт для перевода
            user_message = f"""Переведи название компании с русского на английский: {text}

ВАЖНО:
- Если это аббревиатура (ТДК, СТЕЛЛАР) - переведи буквы в латиницу
- ООО = LLC, АО = JSC, ЗАО = CJSC, ПАО = PJSC, ИП = IE
- Верни ТОЛЬКО переведенное название без объяснений, ссылок и комментариев"""

            data = {
                "modelUri": f"gpt://{cfg['folder_id']}/yandexgpt/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.1,
                    "maxTokens": 200
                },
                "messages": [
                    {"role": "user", "text": user_message}
                ]
            }

            headers = {
                'Authorization': f'Api-Key {cfg["api_key"]}',
                'Content-Type': 'application/json'
            }

            import requests
            _logger.info(f"[ПЕРЕВОД] 🚀 Отправляем запрос к YandexGPT для текста: '{text[:50]}...'")
            _logger.debug(f"[ПЕРЕВОД] 📤 Данные запроса: {data}")
            
            response = requests.post(
                'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
                headers=headers,
                json=data,
                timeout=30
            )
            
            _logger.info(f"[ПЕРЕВОД] 📥 Получен ответ от YandexGPT: статус {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                if 'result' in result and 'alternatives' in result['result']:
                    translated_text = result['result']['alternatives'][0]['message']['text'].strip()
                    
                    # Проверяем качество перевода - не должно быть ссылок или лишнего текста
                    if ('[' in translated_text and ']' in translated_text) or \
                       'http' in translated_text.lower() or \
                       'ya.ru' in translated_text.lower() or \
                       'поиск' in translated_text.lower() or \
                       len(translated_text) > 100:  # Слишком длинный результат
                        _logger.warning(f"[ПЕРЕВОД] Некачественный перевод для '{text}', возвращаем оригинал")
                        return text
                    
                    _logger.info(f"[ПЕРЕВОД] '{text}' -> '{translated_text}'")
                    return translated_text
                else:
                    _logger.error(f"[ПЕРЕВОД] Неожиданный формат ответа: {result}")
                    return text
            else:
                _logger.error(f"[ПЕРЕВОД] Ошибка API: {response.status_code} - {response.text}")
                return text
                
        except Exception as e:
            _logger.error(f"[ПЕРЕВОД] Ошибка при переводе '{text}': {str(e)}")
            return text
    
    def _convert_docx_to_pdf_base64(self, docx_base64, sign_individual=False):
        """Конвертирует DOCX в PDF и возвращает base64. Если sign_individual=True, добавляет подписи агента."""
        import base64
        try:
            # Декодируем DOCX
            docx_bytes = base64.b64decode(docx_base64)

            # Используем существующую функцию конвертации
            # pdf_base64 = self._convert_docx_to_pdf(docx_bytes)

            
            # Для индивидуальных документов используем Spire.Doc для высокой точности форматирования
            if sign_individual:
                _logger.info("🎯 Используем Spire.Doc для конвертации индивидуального документа")
                pdf_base64 = self._convert_docx_to_pdf_spire(docx_bytes)
            else:
                # Для остальных документов используем стандартный метод
                pdf_base64 = self._convert_docx_to_pdf(docx_bytes)
            
            # Если нужно подписать документ "Индивидуал"
            if sign_individual and pdf_base64:
                try:
                    # Декодируем PDF для подписания
                    pdf_bytes = base64.b64decode(pdf_base64)
                    
                    # Определяем тип агента
                    agent_type = self._detect_agent_type_from_record()
                    _logger.info(f"[_convert_docx_to_pdf_base64] Detected agent type for individual document: {agent_type}")
                    
                    # Подписываем документ
                    signed_pdf_bytes = self._sign_individual_document(pdf_bytes, agent_type)
                    
                    # Кодируем обратно в base64
                    pdf_base64 = base64.b64encode(signed_pdf_bytes).decode('utf-8')
                    _logger.info(f"[_convert_docx_to_pdf_base64] Successfully signed individual document with {agent_type} signatures")
                    
                except Exception as sign_error:
                    _logger.error(f"[_convert_docx_to_pdf_base64] Error signing individual document: {sign_error}")
                    # Возвращаем неподписанный PDF в случае ошибки
            
            return pdf_base64
            
        except Exception as e:
            _logger.error(f"Ошибка при конвертации DOCX в PDF: {str(e)}")
            return None
    
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
            _logger.info(f"=== ГЕНЕРАЦИЯ ДОКУМЕНТА АКТ-ОТЧЕТ ДЛЯ ЗАЯВКИ ID {self.id} ===")
            
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
            
            # Генерируем документ с использованием современного метода (как в индивидуалах)
            generated_file = self._generate_document_from_template(template, template_data)
            
            if generated_file:
                file_name = f'Акт-отчет_{self.zayavka_num or self.zayavka_id}.docx'
                file_data = generated_file
                mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                
                # Создаем attachment
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': file_name,
                    'type': 'binary',
                    'datas': file_data,
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': mimetype,
                })
                
                # Добавляем файл в Many2many поле
                self.act_report_attachments = [(4, attachment.id)]
                
                # Увеличиваем счетчик использования шаблона
                template.increment_usage()
                
                # Обновляем запись для автообновления интерфейса
                self.invalidate_recordset()
                
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
        # Для docxtpl используем простые имена переменных без скобок
        final_data = {
            'номер_поручения': instruction_number,
            'дата_генерации_документа': generation_date_formatted,
            'дата_подписания_поручения': instruction_date_formatted,
            'клиент': client_name,
            'агент': agent_name,
            'покупатель_продавец': buyer_seller,
            'номер_контракта': contract_number,
            'вид_сделки': deal_type_text,
            'получен_swift': swift_received_formatted,
            'заявка_по_курсу': application_amount_rub_formatted,
            'сумма_валюта': amount_with_currency,
            'вознагрождение_сбер': sber_reward_formatted,
            'итого_сбер': total_sber_formatted,
            'подитог_текст': sber_reward_text,
        }
        
        _logger.info("=== ФИНАЛЬНЫЕ ДАННЫЕ ИЗ ODOO ДЛЯ ЗАМЕНЫ ===")
        filled_count = 0
        empty_count = 0
        
        for key, value in final_data.items():
            has_data = value and str(value).strip()
            if key == 'подитог_текст':
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
        
        # Получаем страну с переводом на английский если нужно
        country = ""
        if self.country_id and hasattr(self.country_id, 'name') and self.country_id.name:
            country_ru = str(self.country_id.name).strip()
            
            # ПРИОРИТЕТ 1: Проверяем поле "Английское название страны" в модели стран
            if hasattr(self.country_id, 'eng_country_name') and self.country_id.eng_country_name:
                country_en_from_model = str(self.country_id.eng_country_name).strip()
                if country_en_from_model:
                    country = country_en_from_model
                    _logger.info(f"[ЗАЯВЛЕНИЕ] 🎯 Используем английское название из модели: '{country_ru}' -> '{country}'")
                else:
                    # Поле есть, но пустое - переходим к автоматическому переводу
                    _logger.info(f"[ЗАЯВЛЕНИЕ] ⚠️ Поле 'eng_country_name' пустое для '{country_ru}', переходим к автоматическому переводу")
                    country = self._get_country_translation_fallback(country_ru)
            else:
                # ПРИОРИТЕТ 2: Поле отсутствует или не заполнено - используем автоматический перевод
                _logger.info(f"[ЗАЯВЛЕНИЕ] 🔍 Поле 'eng_country_name' отсутствует для '{country_ru}', используем автоматический перевод")
                country = self._get_country_translation_fallback(country_ru)
        
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
        
        # Данные для docxtpl - добавляем множественные варианты именования
        current_date = datetime.now().strftime('%d.%m.%Y')
        amount_str = f"{self.amount:.2f}" if self.amount else "0.00"
        
        template_data = {
            # Основные поля (английские названия)
            'VALUE_DATE': current_date,
            'AMOUNT': amount_str,
            'CURRENCY': currency_display,
            'BILL_TO': bill_to,
            'BENEFICIARY': beneficiary,
            'BENEFICIARY_COUNTRY': country,
            'BENEFICIARY_ADDRESS': beneficiary_addr,
            'ACCOUNT': self.iban_accc or "",
            'BENEF_BANK': self.beneficiary_bank_name or "",
            'ADDRESS': self.bank_address or "",
            'SWIFT': self.bank_swift or "",
            'PAYMENT_DETAILS': payment_details,
            
            # Варианты с пробелами и звездочками
            'VALUE DATE': current_date,
            'VALUE DATE*': current_date,
            'VALUE DATE *': current_date,
            'AMOUNT*': amount_str,
            'AMOUNT *': amount_str,
            'CURRENCY*': currency_display,
            'CURRENCY *': currency_display,
            'BILL TO': bill_to,
            'BILL TO*': bill_to,
            'BILL TO *': bill_to,
            'BENEFICIARY*': beneficiary,
            'BENEFICIARY *': beneficiary,
            'BENEFICIARY COUNTRY': country,
            'BENEFICIARY COUNTRY*': country,
            'BENEFICIARY COUNTRY *': country,
            'BENEFICIARY ADDRESS': beneficiary_addr,
            'BENEFICIARY ADDRESS*': beneficiary_addr,
            'BENEFICIARY ADDRESS *': beneficiary_addr,
            'ACCOUNT*': self.iban_accc or "",
            'ACCOUNT *': self.iban_accc or "",
            'BENEF BANK': self.beneficiary_bank_name or "",
            'BENEF.BANK': self.beneficiary_bank_name or "",
            'BENEF.BANK*': self.beneficiary_bank_name or "",
            'BENEF.BANK *': self.beneficiary_bank_name or "",
            'ADDRESS*': self.bank_address or "",
            'ADDRESS *': self.bank_address or "", 
            'SWIFT*': self.bank_swift or "",
            'SWIFT *': self.bank_swift or "",
            'PAYMENT DETAILS': payment_details,
            'PAYMENT DETAILS*': payment_details,
            'PAYMENT DETAILS *': payment_details,
            
            # Возможные русские варианты
            'дата': current_date,
            'сумма': amount_str,
            'валюта': currency_display,
            'плательщик': bill_to,
            'получатель': beneficiary,
            'страна_получателя': country,
            'адрес_получателя': beneficiary_addr,
            'счет': self.iban_accc or "",
            'банк_получателя': self.beneficiary_bank_name or "",
            'адрес_банка': self.bank_address or "",
            'свифт': self.bank_swift or "",
            'назначение_платежа': payment_details,
            
            # Возможные варианты с номером заявки
            'номер_заявки': self.zayavka_num or self.zayavka_id or "",
            'zayavka_num': self.zayavka_num or self.zayavka_id or "",
            'zayavka_id': str(self.zayavka_id) if self.zayavka_id else "",
        }
        
        # КРИТИЧЕСКИ ВАЖНО: Убеждаемся что ВСЕ значения являются строками
        # docxtpl не может обрабатывать булевы значения, числа и None
        safe_template_data = {}
        for key, value in template_data.items():
            if value is None:
                safe_template_data[key] = ""
            elif isinstance(value, bool):
                safe_template_data[key] = "Да" if value else "Нет"
            elif isinstance(value, (int, float)):
                safe_template_data[key] = str(value)
            else:
                safe_template_data[key] = str(value)
        
        _logger.info("=== ФИНАЛЬНЫЕ ДАННЫЕ ДЛЯ ШАБЛОНА ===")
        for key, value in safe_template_data.items():
            _logger.info(f"'{key}': '{value}' (тип: {type(value).__name__})")
        _logger.info("=== КОНЕЦ ДАННЫХ ===")
        
        return safe_template_data
    
    def _generate_document_from_template(self, template, template_data):
        """Генерирует документ из шаблона с подстановкой данных"""
        import base64
        import tempfile
        import os
        
        try:
            # КРИТИЧЕСКАЯ ПРОВЕРКА: проверяем поле template_file
            _logger.info(f"🔍 ПРОВЕРКА ШАБЛОНА:")
            _logger.info(f"  template.id: {template.id}")
            _logger.info(f"  template.name: {template.name}")
            _logger.info(f"  template_file тип: {type(template.template_file).__name__}")
            _logger.info(f"  template_file значение: {repr(template.template_file)[:100]}...")
            
            if not template.template_file:
                raise ValueError("Поле template_file пустое!")
            
            if isinstance(template.template_file, bool):
                raise ValueError(f"Поле template_file имеет булев тип: {template.template_file}")
            
            # Декодируем файл шаблона
            _logger.info("🚀 Вызываем base64.b64decode()...")
            template_bytes = base64.b64decode(template.template_file)
            _logger.info(f"✅ base64.b64decode() выполнен успешно, получено {len(template_bytes)} байт")
            
            # Создаем временный файл для работы
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(template_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Обрабатываем DOCX файл
                processed_doc = self._process_docx_template(temp_file_path, template_data)
                
                # Если получили объект DocxTemplate, сохраняем его в байты
                if hasattr(processed_doc, 'save'):
                    # docxtpl возвращает объект DocxTemplate
                    # Используем delete=False чтобы файл не удалился преждевременно
                    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as result_file:
                        result_file_path = result_file.name
                    
                    try:
                        # Сохраняем документ
                        processed_doc.save(result_file_path)
                        # Читаем байты
                        with open(result_file_path, 'rb') as f:
                            result_bytes = f.read()
                    finally:
                        # Удаляем временный файл
                        try:
                            os.unlink(result_file_path)
                        except Exception:
                            pass
                else:
                    # Старый метод возвращает байты напрямую
                    result_bytes = processed_doc
                
                return base64.b64encode(result_bytes).decode('utf-8')
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            _logger.error(f"Ошибка при генерации документа из шаблона: {str(e)}")
            return None
    
    def _generate_statement_document_from_template(self, template, template_data):
        """Генерирует документ заявления из шаблона с использованием docxtpl (безопасный подход)"""
        import base64
        import tempfile
        import os
        
        try:
            _logger.info("[ЗАЯВЛЕНИЕ] Используем безопасный метод генерации с docxtpl")
            
            # Декодируем файл шаблона
            template_bytes = base64.b64decode(template.template_file)
            
            # Создаем временный файл для работы
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(template_bytes)
                temp_file_path = temp_file.name
            
            try:
                # ИСПОЛЬЗУЕМ ТОТ ЖЕ БЕЗОПАСНЫЙ МЕТОД, ЧТО И ДЛЯ АКТОВ/ИНДИВИДУАЛОВ
                processed_doc = self._process_docx_template(temp_file_path, template_data)
                
                # Если получили объект DocxTemplate, сохраняем его в байты
                if hasattr(processed_doc, 'save'):
                    # docxtpl возвращает объект DocxTemplate
                    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as result_file:
                        result_file_path = result_file.name
                    
                    try:
                        # Сохраняем документ
                        processed_doc.save(result_file_path)
                        # Читаем байты
                        with open(result_file_path, 'rb') as f:
                            result_bytes = f.read()
                        
                        _logger.info("[ЗАЯВЛЕНИЕ] ✅ Документ успешно сгенерирован с docxtpl")
                        return base64.b64encode(result_bytes).decode('utf-8')
                    finally:
                        # Удаляем временный файл
                        try:
                            os.unlink(result_file_path)
                        except Exception:
                            pass
                else:
                    # Старый метод возвращает байты напрямую
                    if processed_doc:
                        _logger.info("[ЗАЯВЛЕНИЕ] ✅ Документ успешно сгенерирован (legacy метод)")
                        return base64.b64encode(processed_doc).decode('utf-8')
                    else:
                        _logger.error("[ЗАЯВЛЕНИЕ] ❌ Не удалось сгенерировать документ")
                        return None
                        
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            _logger.error(f"[ЗАЯВЛЕНИЕ] Ошибка при генерации документа заявления: {str(e)}")
            import traceback
            _logger.error(f"[ЗАЯВЛЕНИЕ] Traceback: {traceback.format_exc()}")
            return None
    
    def _process_docx_template(self, docx_path, template_data):
        """Обрабатывает DOCX шаблон с помощью docxtpl - современный и надежный подход"""
        try:
            _logger.info(f"[_process_docx_template] Начинаем обработку шаблона с docxtpl: {docx_path}")
            
            # Импортируем docxtpl
            try:
                from docxtpl import DocxTemplate  # type: ignore
            except ImportError:
                _logger.error("docxtpl не установлен! Используем старый метод...")
                return self._process_docx_template_legacy(docx_path, template_data)
            
            # Создаем объект шаблона
            doc = DocxTemplate(docx_path)
            
            _logger.info("=== ОТЛАДКА DOCXTPL ОБРАБОТКИ ===")
            _logger.info(f"Данные для замены: {template_data}")
            _logger.info(f"Количество переменных: {len(template_data)}")
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: убеждаемся что все значения - строки
            _logger.info("🔍 ПРОВЕРКА ТИПОВ ДАННЫХ ПЕРЕД DOCXTPL:")
            for key, value in template_data.items():
                value_type = type(value).__name__
                _logger.info(f"  '{key}': {value_type} = '{value}'")
                if not isinstance(value, str):
                    _logger.error(f"❌ НАЙДЕНО НЕ-СТРОКОВОЕ ЗНАЧЕНИЕ: '{key}' имеет тип {value_type}")
            
            # Рендерим шаблон с данными
            try:
                _logger.info("🚀 Вызываем doc.render() с проверенными данными...")
                doc.render(template_data)
                _logger.info("✅ doc.render() выполнен успешно!")
            except Exception as render_error:
                _logger.error(f"❌ ОШИБКА В doc.render(): {render_error}")
                _logger.error(f"❌ Тип ошибки: {type(render_error).__name__}")
                raise render_error
            
            _logger.info("✅ docxtpl успешно обработал шаблон!")
            _logger.info("=== КОНЕЦ ОТЛАДКИ DOCXTPL ===")
            
            return doc
            
        except Exception as e:
            _logger.error(f"[_process_docx_template] Ошибка при обработке с docxtpl: {e}")
            _logger.info("Переходим на резервный метод...")
            return self._process_docx_template_legacy(docx_path, template_data)
    
    def _process_docx_template_legacy(self, docx_path, template_data):
        """РЕЗЕРВНЫЙ метод: Обрабатывает DOCX шаблон через XML (старый подход)"""
        import tempfile
        import os
        from zipfile import ZipFile
        
        try:
            _logger.info(f"[_process_docx_template_legacy] Начинаем обработку шаблона: {docx_path}")
            
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
                    
                    _logger.info("=== ОТЛАДКА DOCX ОБРАБОТКИ (LEGACY) ===")
                    _logger.info(f"Данные для замены: {template_data}")
                    _logger.info(f"Размер XML содержимого: {len(content)} символов")
                    
                    # КРИТИЧЕСКАЯ ПРОВЕРКА: убеждаемся что все значения - строки
                    _logger.info("🔍 ПРОВЕРКА ТИПОВ ДАННЫХ ПЕРЕД LEGACY ОБРАБОТКОЙ:")
                    for key, value in template_data.items():
                        value_type = type(value).__name__
                        _logger.info(f"  '{key}': {value_type} = '{value}'")
                        if not isinstance(value, str):
                            _logger.error(f"❌ НАЙДЕНО НЕ-СТРОКОВОЕ ЗНАЧЕНИЕ: '{key}' имеет тип {value_type}")
                    
                    # Покажем небольшой образец содержимого для анализа
                    preview_start = content[:300].replace('\n', '\\n').replace('\r', '\\r')
                    _logger.info(f"Начало XML: {preview_start}...")
                    
                    # Счетчик замен
                    total_replacements = 0
                    
                    # Импортируем re для обработки разбитых сигнатур
                    import re
                    
                    # Экранируем XML символы в значениях И фигурные скобки (чтобы они не воспринимались как новые сигнатуры)
                    def escape_xml(text):
                        """Экранирует XML символы и фигурные скобки в значениях"""
                        _logger.info(f"🔧 escape_xml вызвана с: {repr(text)} (тип: {type(text).__name__})")
                        
                        if not isinstance(text, str):
                            _logger.info(f"⚠️ Преобразуем {type(text).__name__} в строку: {text}")
                            text = str(text)
                        
                        # Сначала проверяем, не экранирован ли уже символ &
                        if '&amp;' not in text:
                            text = text.replace('&', '&amp;')
                        result = (text.replace('<', '&lt;')
                               .replace('>', '&gt;')
                               .replace('"', '&quot;')
                               .replace("'", '&apos;'))
                        
                        _logger.info(f"🔧 escape_xml результат: {repr(result)}")
                        return result
                        # НЕ экранируем фигурные скобки в данных - это может сломать XML
                    
                    # УПРОЩЕННАЯ ЛОГИКА: Используем только наши данные для замены
                    _logger.info("=== ПРОВЕРКА НАШИХ СИГНАТУР В ДОКУМЕНТЕ ===")
                    for template_key in template_data.keys():
                        if template_key in content:
                            _logger.info(f"✅ НАЙДЕНА В ДОКУМЕНТЕ: '{template_key}'")
                        else:
                            _logger.info(f"❌ НЕ НАЙДЕНА В ДОКУМЕНТЕ: '{template_key}'")
                            
                            # ДИАГНОСТИКА: Ищем части сигнатуры
                            inner_text = template_key.strip('{}[]')
                            if inner_text in content:
                                _logger.info(f"🔍 НАЙДЕН ВНУТРЕННИЙ ТЕКСТ: '{inner_text}' (сигнатура разбита!)")
                                
                                # Ищем контекст вокруг найденного текста
                                pattern = f'.{{0,50}}{re.escape(inner_text)}.{{0,50}}'
                                matches = re.findall(pattern, content, re.DOTALL)
                                if matches:
                                    for i, match in enumerate(matches[:2]):  # Показываем первые 2 совпадения
                                        clean_match = match.replace('\n', ' ').replace('\r', ' ')
                                        _logger.info(f"📍 КОНТЕКСТ {i+1}: ...{clean_match}...")
                            else:
                                _logger.info(f"🚫 ВНУТРЕННИЙ ТЕКСТ '{inner_text}' ТОЖЕ НЕ НАЙДЕН!")
                    
                    # ПРОСТАЯ ЗАМЕНА КАК В АКТ-ОТЧЕТЕ: Заменяем каждую сигнатуру
                    _logger.info("=== ПРОСТАЯ ЗАМЕНА СИГНАТУР (КАК В АКТ-ОТЧЕТЕ) ===")
                    for signature, value in template_data.items():
                        # Если значение пустое - просто убираем сигнатуру
                        if not value or str(value).strip() == "":
                            _logger.info(f"[УДАЛЕНИЕ] Убираем пустую сигнатуру: '{signature}'")
                            if signature in content:
                                content = content.replace(signature, "")
                                total_replacements += 1
                                _logger.info(f"✅ Удалена: '{signature}'")
                            continue
                        
                        # Экранируем значение для безопасности XML
                        safe_value = escape_xml(str(value))
                        
                        # Простая замена - как в акт-отчете
                        if signature in content:
                            replacements_count = content.count(signature)
                            content = content.replace(signature, safe_value)
                            total_replacements += replacements_count
                            _logger.info(f"✅ [ПРОСТАЯ ЗАМЕНА] '{signature}' -> '{safe_value}' ({replacements_count} раз)")
                        else:
                            # Если простая замена не сработала, пробуем разбитую сигнатуру
                            _logger.info(f"[РАЗБИТАЯ] Пробуем разбитую сигнатуру для: '{signature}'")
                            replaced_content = self._replace_broken_signature(content, signature, safe_value, escape_xml)
                            if replaced_content != content:
                                content = replaced_content
                                total_replacements += 1
                                _logger.info(f"✅ [РАЗБИТАЯ ЗАМЕНА] '{signature}' -> '{safe_value}'")
                            else:
                                _logger.info(f"❌ [НЕ НАЙДЕНА] '{signature}' отсутствует в документе")
                    
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
                    
                    # Квадратные скобки ВКЛЮЧЕНЫ - они есть в шаблоне!
                    for bracket_sig in all_bracket_signatures:
                        remaining_signatures.append(bracket_sig)
                    if remaining_signatures:
                        _logger.warning(f"⚠️  ОСТАЛИСЬ НЕОБРАБОТАННЫЕ СИГНАТУРЫ: {len(remaining_signatures)} штук")
                        _logger.info("🧹 ОТКЛЮЧАЕМ агрессивную очистку - основная замена работает хорошо")
                        
                        # АГРЕССИВНАЯ ОЧИСТКА ОТКЛЮЧЕНА - основная замена работает хорошо
                        _logger.info("✅ Основная замена завершена успешно - агрессивная очистка не требуется")
                    else:
                        _logger.info("✅ Все сигнатуры успешно обработаны!")
                    
                    _logger.info("=== КОНЕЦ ОБРАБОТКИ СИГНАТУР ===")
                    
                    # ФИНАЛЬНАЯ ОЧИСТКА: Удаляем оставшиеся пустые скобки
                    _logger.info("🧹 Финальная очистка оставшихся скобок...")
                    
                    import re
                    # Удаляем пустые скобки всех типов
                    cleanup_patterns = [
                        r'\{\{\s*\}\}',  # {{}}
                        r'\[\[\s*\]\]',  # [[]]
                        r'\[\s*\]',      # []
                        r'\{\s*\}',      # {}
                    ]
                    
                    cleaned_count = 0
                    for pattern in cleanup_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            content = re.sub(pattern, '', content)
                            cleaned_count += len(matches)
                            _logger.info(f"🗑️  Удалено {len(matches)} пустых скобок: {pattern}")
                    
                    if cleaned_count > 0:
                        _logger.info(f"✅ Финальная очистка завершена: удалено {cleaned_count} пустых скобок")
                    else:
                        _logger.info("✅ Пустых скобок не найдено")
                    
                    # Проверяем валидность XML перед сохранением
                    try:
                        # Дополнительная очистка XML перед валидацией
                        # Убираем возможные проблемные символы
                        content_clean = content.replace('&amp;amp;', '&amp;')  # Двойное экранирование
                        content_clean = content_clean.replace('&lt;lt;', '&lt;')  # Двойное экранирование
                        content_clean = content_clean.replace('&gt;gt;', '&gt;')  # Двойное экранирование
                        
                        ET.fromstring(content_clean)
                        content = content_clean  # Используем очищенную версию
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
        """ПРОСТОЙ И НАДЕЖНЫЙ алгоритм замены разбитых сигнатур"""
        import re
        import xml.etree.ElementTree as ET
        
        try:
            _logger.info(f"[_replace_broken_signature] Ищем разбитую сигнатуру: {signature}")
            
            # Получаем внутренний текст без скобок
            inner_text = signature.strip('{}[]')
            _logger.info(f"[_replace_broken_signature] Внутренний текст: {inner_text}")
            
            escaped_value = escape_xml_func(value)
            original_content = xml_content
            
            # ОТКЛЮЧАЕМ REGEX - он портит XML структуру!
            # Используем только безопасную замену по частям
            
            # МЕТОД 3: Разбиваем по частям (только если есть подчеркивания)
            if '_' in inner_text:
                parts = inner_text.split('_')
                _logger.info(f"[_replace_broken_signature] Ищем части сигнатуры: {parts}")
                
                # Проверяем, есть ли все части в документе
                found_parts = []
                for part in parts:
                    if part and part in xml_content:
                        found_parts.append(part)
                
                if len(found_parts) >= 2:  # Нужно минимум 2 части
                    _logger.info(f"[_replace_broken_signature] Найдены части: {found_parts}")
                    
                    # Заменяем первую часть на значение
                    xml_content = xml_content.replace(found_parts[0], escaped_value, 1)
                    
                    # Удаляем остальные части
                    for part in found_parts[1:]:
                        xml_content = xml_content.replace('_' + part, '', 1)
                        xml_content = xml_content.replace(part, '', 1)
                    
                    # НЕ УДАЛЯЕМ скобки глобально - это портит XML структуру!
                    # Скобки могут быть частью других XML элементов
                    
                    # Проверяем валидность XML
                    try:
                        ET.fromstring(xml_content)
                        _logger.info(f"[_replace_broken_signature] Замена по частям выполнена успешно")
                        return xml_content
                    except ET.ParseError as e:
                        _logger.warning(f"[_replace_broken_signature] XML поврежден: {e}")
                        return original_content
            else:
                # ДЛЯ СИГНАТУР БЕЗ ПОДЧЕРКИВАНИЙ: Пробуем точную замену XML тега
                if inner_text in xml_content:
                    _logger.info(f"[_replace_broken_signature] Найден цельный внутренний текст: {inner_text}")
                    
                    # ТОЧНАЯ замена XML тега: <w:t>inner_text</w:t> → <w:t>escaped_value</w:t>
                    import re
                    pattern = f'<w:t>{re.escape(inner_text)}</w:t>'
                    replacement = f'<w:t>{escaped_value}</w:t>'
                    
                    if re.search(pattern, xml_content):
                        xml_content = re.sub(pattern, replacement, xml_content, count=1)
                        _logger.info(f"[_replace_broken_signature] Выполнена точная замена XML тега")
                        
                        # Проверяем валидность XML
                        try:
                            ET.fromstring(xml_content)
                            _logger.info(f"[_replace_broken_signature] ✅ Точная замена XML тега выполнена успешно")
                            return xml_content
                        except ET.ParseError as e:
                            _logger.warning(f"[_replace_broken_signature] XML поврежден после точной замены: {e}")
                            return original_content
                    else:
                        _logger.info(f"[_replace_broken_signature] XML тег <w:t>{inner_text}</w:t> не найден, пробуем простую замену")
                        
                        # Fallback: простая замена как последняя попытка
                        xml_content = xml_content.replace(inner_text, escaped_value, 1)
                        
                        # Проверяем валидность XML
                        try:
                            ET.fromstring(xml_content)
                            _logger.info(f"[_replace_broken_signature] ✅ Простая замена выполнена успешно")
                            return xml_content
                        except ET.ParseError as e:
                            _logger.warning(f"[_replace_broken_signature] XML поврежден после простой замены: {e}")
                            return original_content
            
            _logger.info(f"[_replace_broken_signature] Не удалось найти сигнатуру: {signature}")
            return xml_content
            
        except Exception as e:
            _logger.error(f"[_replace_broken_signature] Ошибка: {e}")
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
            'beneficiary countryстрана получателя': 'BENEFICIARY COUNTRY*',
            'beneficiary country': 'BENEFICIARY COUNTRY*',
            'страна получателя': 'BENEFICIARY COUNTRY*',
            
            # BENEFICIARY ADDRESS - адрес получателя
            'beneficiary address адрес получателя (город просьба указать)': 'BENEFICIARY ADDRESS*',
            'beneficiary address': 'BENEFICIARY ADDRESS*',
            'адрес получателя': 'BENEFICIARY ADDRESS*',
            
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
 