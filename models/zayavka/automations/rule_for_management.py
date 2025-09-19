from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ZayavkaRuleForManagement(models.Model):
    _inherit = 'amanat.zayavka'

    @api.model
    def apply_rules_by_deal_closed_date(self):
        # 3. Очищаем ссылки
        self.write({
            'payment_order_rule_id': False,
            'expense_rule_id': False,
            'money_cost_rule_id': False,
        })

        # 4. Получаем дату и сумму
        deal_closed_date = self.deal_closed_date
        equivalent_sum = self.equivalent_amount_usd
        contragent = self.contragent_id
        agent = self.agent_id
        client = self.client_id
        currency = self.currency
        
        if not deal_closed_date:
            _logger.error(f'Поле "сделка закрыта" пустое у заявки {self.id}.')
            return

        if equivalent_sum is None:
            _logger.warning(f'Поле "equivalent_amount_usd" пустое у заявки {self.id}.')
            return

        # 5. Поиск подходящих записей с учетом даты и суммы
        def find_matching_rule(model, date_field_start, date_field_end):
            # Сначала получаем все записи, подходящие по базовым условиям (дата и сумма)
            base_domain = [
                (date_field_start, '<=', deal_closed_date),
                (date_field_end, '>=', deal_closed_date),
                ('min_application_amount', '<=', equivalent_sum),
                ('max_application_amount', '>=', equivalent_sum),
            ]
            
            candidate_rules = self.env[model].search(base_domain)
            _logger.info(f"[find_matching_rule] Найдено {len(candidate_rules)} кандидатов в модели {model} по базовым условиям")
            
            if not candidate_rules:
                _logger.warning(f"[find_matching_rule] В модели {model} нет записей, подходящих по дате и сумме!")
                return None
            
            # Фильтруем кандидатов и вычисляем вес специфичности
            matching_rules = []
            
            for rule in candidate_rules:
                _logger.info(f"[find_matching_rule] Проверяем правило {model} ID={rule.id}: {getattr(rule, 'name', 'без названия')}")
                
                # Получаем значения полей правила
                contragent_rule = getattr(rule, 'contragent_zayavka_id', None)
                agent_rule = getattr(rule, 'agent_zayavka_id', None)
                client_rule = getattr(rule, 'client_zayavka_id', None)
                currency_rule = getattr(rule, 'currency_zayavka', None)
                
                # Проверяем совместимость: пустое поле в правиле = подходит ЛЮБОЕ значение в заявке
                contragent_ok = (not contragent_rule) or (contragent_rule and contragent and contragent_rule.id == contragent.id)
                agent_ok = (not agent_rule) or (agent_rule and agent and agent_rule.id == agent.id)
                client_ok = (not client_rule) or (client_rule and client and client_rule.id == client.id)
                currency_ok = (not currency_rule) or (currency_rule and currency and currency_rule == currency)
                
                # Если все условия выполнены, добавляем в список подходящих
                if contragent_ok and agent_ok and client_ok and currency_ok:
                    # Вычисляем вес специфичности = количество непустых полей в правиле, которые совпадают с заявкой
                    specificity_weight = 0
                    
                    if contragent_rule and contragent and contragent_rule.id == contragent.id:
                        specificity_weight += 1
                    if agent_rule and agent and agent_rule.id == agent.id:
                        specificity_weight += 1
                    if client_rule and client and client_rule.id == client.id:
                        specificity_weight += 1
                    if currency_rule and currency and currency_rule == currency:
                        specificity_weight += 1
                    
                    matching_rules.append((rule, specificity_weight))
                    _logger.info(f"  ✅ Правило подходит! Вес специфичности: {specificity_weight}")
                else:
                    _logger.info("  ❌ Правило не подходит")
            
            if not matching_rules:
                _logger.warning(f"[find_matching_rule] Не найдено подходящих правил в модели {model}")
                return None
            
            # Сортируем по убыванию веса специфичности (наиболее специфичные первыми)
            matching_rules.sort(key=lambda x: x[1], reverse=True)
            
            # Выбираем наиболее специфичное правило
            best_rule, best_weight = matching_rules[0]
            
            _logger.info(f"[find_matching_rule] ✅ Выбрано наиболее специфичное правило {model}: ID={best_rule.id} (название: {getattr(best_rule, 'name', 'без названия')}), вес: {best_weight}")
            
            # Логируем все найденные правила для понимания выбора
            if len(matching_rules) > 1:
                _logger.info("[find_matching_rule] Другие подходящие правила:")
                for rule, weight in matching_rules[1:]:
                    _logger.info(f"  - ID={rule.id} (название: {getattr(rule, 'name', 'без названия')}), вес: {weight}")
            
            return best_rule

        payment_rule = find_matching_rule('amanat.payment_order_rule', 'date_start', 'date_end')
        expense_rule = find_matching_rule('amanat.expense_rule', 'date_start', 'date_end')
        cost_rule    = find_matching_rule('amanat.money_cost_rule', 'date_start', 'date_end')

        # 6. Обновляем заявку
        self.write({
            'payment_order_rule_id': payment_rule.id if payment_rule else False,
            'expense_rule_id': expense_rule.id if expense_rule else False,
            'money_cost_rule_id': cost_rule.id if cost_rule else False,
        })

        _logger.info(f'{self.zayavka_id} установлены следующие поля: payment_order_rule_id = {payment_rule}, expense_rule_id = {expense_rule}, money_cost_rule_id = {cost_rule}')

    @api.model
    def apply_rules_by_rate_fixation_date(self):
        """
        Применяет правила управления по дате фиксации курса (для автоматизации "Обновить список правил")
        Использует rate_fixation_date вместо deal_closed_date
        """
        # Очищаем ссылки
        self.write({
            'payment_order_rule_id': False,
            'expense_rule_id': False,
            'money_cost_rule_id': False,
        })

        # Получаем дату и сумму
        rate_fixation_date = self.deal_closed_date
        equivalent_sum = self.equivalent_amount_usd
        contragent = self.contragent_id
        agent = self.agent_id
        client = self.client_id
        currency = self.currency
        
        # Если нет даты фиксации курса, используем текущую дату
        if not rate_fixation_date:
            from datetime import date
            rate_fixation_date = date.today()
            _logger.info(f'[RULE_AUTOMATION] Заявка {self.id}: поле "rate_fixation_date" пустое, используем текущую дату: {rate_fixation_date}')
        else:
            _logger.info(f'[RULE_AUTOMATION] Заявка {self.id}: используем дату фиксации курса: {rate_fixation_date}')

        if equivalent_sum is None:
            _logger.warning(f'[RULE_AUTOMATION] Заявка {self.id}: поле "equivalent_amount_usd" пустое.')
            return

        _logger.info(f'[RULE_AUTOMATION] Заявка {self.id}: поиск правил по дате={rate_fixation_date}, сумма={equivalent_sum}, контрагент={contragent.name if contragent else None}, агент={agent.name if agent else None}, клиент={client.name if client else None}, валюта={currency}')

        # Поиск подходящих записей с учетом даты и суммы
        def find_matching_rule(model, date_field_start, date_field_end):
            # Сначала получаем все записи, подходящие по базовым условиям (дата и сумма)
            base_domain = [
                (date_field_start, '<=', rate_fixation_date),
                (date_field_end, '>=', rate_fixation_date),
                ('min_application_amount', '<=', equivalent_sum),
                ('max_application_amount', '>=', equivalent_sum),
            ]
            
            candidate_rules = self.env[model].search(base_domain)
            _logger.info(f"[RULE_AUTOMATION] Найдено {len(candidate_rules)} кандидатов в модели {model} по базовым условиям")
            
            if not candidate_rules:
                _logger.warning(f"[RULE_AUTOMATION] В модели {model} нет записей, подходящих по дате и сумме!")
                return None
            
            # Фильтруем кандидатов и вычисляем вес специфичности
            matching_rules = []
            
            for rule in candidate_rules:
                _logger.info(f"[RULE_AUTOMATION] Проверяем правило {model} ID={rule.id}: {getattr(rule, 'name', 'без названия')}")
                
                # Получаем значения полей правила
                contragent_rule = getattr(rule, 'contragent_zayavka_id', None)
                agent_rule = getattr(rule, 'agent_zayavka_id', None)
                client_rule = getattr(rule, 'client_zayavka_id', None)
                currency_rule = getattr(rule, 'currency_zayavka', None)
                
                # Проверяем совместимость: пустое поле в правиле = подходит ЛЮБОЕ значение в заявке
                contragent_ok = (not contragent_rule) or (contragent_rule and contragent and contragent_rule.id == contragent.id)
                agent_ok = (not agent_rule) or (agent_rule and agent and agent_rule.id == agent.id)
                client_ok = (not client_rule) or (client_rule and client and client_rule.id == client.id)
                currency_ok = (not currency_rule) or (currency_rule and currency and currency_rule == currency)
                
                _logger.info(f"  Контрагент ({contragent_rule} vs {contragent}): {'✓' if contragent_ok else '✗'}")
                _logger.info(f"  Агент ({agent_rule} vs {agent}): {'✓' if agent_ok else '✗'}")
                _logger.info(f"  Клиент ({client_rule} vs {client}): {'✓' if client_ok else '✗'}")
                _logger.info(f"  Валюта ({currency_rule} vs {currency}): {'✓' if currency_ok else '✗'}")
                
                # Если все условия выполнены, добавляем в список подходящих
                if contragent_ok and agent_ok and client_ok and currency_ok:
                    # Вычисляем вес специфичности = количество непустых полей в правиле, которые совпадают с заявкой
                    specificity_weight = 0
                    
                    if contragent_rule and contragent and contragent_rule.id == contragent.id:
                        specificity_weight += 1
                    if agent_rule and agent and agent_rule.id == agent.id:
                        specificity_weight += 1
                    if client_rule and client and client_rule.id == client.id:
                        specificity_weight += 1
                    if currency_rule and currency and currency_rule == currency:
                        specificity_weight += 1
                    
                    matching_rules.append((rule, specificity_weight))
                    _logger.info(f"  ✅ Правило подходит! Вес специфичности: {specificity_weight}")
                else:
                    _logger.info("  ❌ Правило не подходит")
                    
                _logger.info("  " + "-" * 50)
            
            if not matching_rules:
                _logger.warning(f"[RULE_AUTOMATION] Не найдено подходящих правил в модели {model}")
                return None
            
            # Сортируем по убыванию веса специфичности (наиболее специфичные первыми)
            matching_rules.sort(key=lambda x: x[1], reverse=True)
            
            # Выбираем наиболее специфичное правило
            best_rule, best_weight = matching_rules[0]
            
            _logger.info(f"[RULE_AUTOMATION] ✅ Выбрано наиболее специфичное правило {model}: ID={best_rule.id} (название: {getattr(best_rule, 'name', 'без названия')}), вес: {best_weight}")
            
            # Логируем все найденные правила для понимания выбора
            if len(matching_rules) > 1:
                _logger.info("[RULE_AUTOMATION] Другие подходящие правила:")
                for rule, weight in matching_rules[1:]:
                    _logger.info(f"  - ID={rule.id} (название: {getattr(rule, 'name', 'без названия')}), вес: {weight}")
            
            return best_rule

        payment_rule = find_matching_rule('amanat.payment_order_rule', 'date_start', 'date_end')
        expense_rule = find_matching_rule('amanat.expense_rule', 'date_start', 'date_end')
        cost_rule = find_matching_rule('amanat.money_cost_rule', 'date_start', 'date_end')

        # Обновляем заявку
        update_vals = {
            'payment_order_rule_id': payment_rule.id if payment_rule else False,
            'expense_rule_id': expense_rule.id if expense_rule else False,
            'money_cost_rule_id': cost_rule.id if cost_rule else False,
        }
        
        self.write(update_vals)

        _logger.info(f'[RULE_AUTOMATION] Заявка {self.zayavka_id} обновлена: payment_order_rule_id = {payment_rule.id if payment_rule else "не найдено"}, expense_rule_id = {expense_rule.id if expense_rule else "не найдено"}, money_cost_rule_id = {cost_rule.id if cost_rule else "не найдено"}')
