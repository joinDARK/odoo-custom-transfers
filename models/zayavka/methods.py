# -*- coding: utf-8 -*-
import logging
import requests
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
                rec.status = '21'
                rec.apply_rules_by_deal_closed_date()
        
        if 'report_link' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'report_link' для заявки {rec.id}")
                if not vals.get('deal_closed_date'):
                    rec.deal_closed_date = fields.Date.today()
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
                rec.run_link_jess_rate_automation()
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

        if 'supplier_currency_paid_date_again_1' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_1' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method()
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission))
        
        if 'supplier_currency_paid_date_again_2' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_2' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission))
        
        if 'supplier_currency_paid_date_again_3' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_3' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission))

        if 'supplier_currency_paid_date_again_4' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_4' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission))

        if 'supplier_currency_paid_date_again_5' in vals:
            for rec in self:
                _logger.info(f"Изменено поле 'supplier_currency_paid_date_again_5' для заявки {rec.id}")
                rec.run_return_with_subsequent_payment_method_new_subagent(rec.amount - (rec.amount * rec.return_commission))

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
            res.run_link_jess_rate_automation()
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
            res.status = '12'

        if vals.get('deal_closed_date'):
            res.status = '21'

        if vals.get('report_link'):
            if not vals.get('deal_closed_date'):
                res.deal_closed_date = fields.Date.today()
            res.status = '21'

        if vals.get('zayavka_attachments'):
            res._analyze_and_log_document_text()

        if vals.get('screen_sber_attachments'):
            res.analyze_screen_sber_images_with_yandex_gpt()

        if vals.get('invoice_attachments'):
            res.invoice_date = fields.Date.today()
            res.status = '2'
        
        if vals.get('payment_order_date_to_client_account'):
            _logger.info("Возврат основной суммы")
            res.run_return_with_main_amount()
        
        if vals.get('payment_order_date_to_client_account_return_all'):
            _logger.info("Возврат всей суммы")
            res.run_return_with_all_amount_method()

        if vals.get('payment_order_date_to_return'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_partial_payment_of_remuneration_method()
        
        if vals.get('supplier_currency_paid_date_again_1'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method()
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission))
        
        if vals.get('supplier_currency_paid_date_again_2'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission))

        if vals.get('supplier_currency_paid_date_again_3'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission))

        if vals.get('supplier_currency_paid_date_again_4'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission))

        if vals.get('supplier_currency_paid_date_again_5'):
            _logger.info("Возврат частичной суммы")
            res.run_return_with_subsequent_payment_method_new_subagent(res.amount - (res.amount * res.return_commission))

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