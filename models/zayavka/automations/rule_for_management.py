from odoo import models, fields, api
from datetime import datetime
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
            domain = [
                (date_field_start, '<=', deal_closed_date),
                (date_field_end, '>=', deal_closed_date),
                ('min_application_amount', '<=', equivalent_sum),
                ('max_application_amount', '>=', equivalent_sum),
            ]
            
            # ИСПРАВЛЕНА ЛОГИКА ДОМЕНА: ищем правила ИЛИ с конкретным значением ИЛИ с пустым полем
            if contragent:
                domain.append(('contragent_zayavka_id', '=', contragent.id))
            else:
                domain.append(('contragent_zayavka_id', '=', False))
                
            if agent:
                domain.append(('agent_zayavka_id', '=', agent.id))
            else:
                domain.append(('agent_zayavka_id', '=', False))
            
            if client:
                domain.append(('client_zayavka_id', '=', client.id))
            else:
                domain.append(('client_zayavka_id', '=', False))

            if currency:
                domain.append(('currency_zayavka', '=', currency))
            else:
                domain.append(('currency_zayavka', '=', False))

            softDomain = [
                (date_field_start, '<=', deal_closed_date),
                (date_field_end, '>=', deal_closed_date),
                ('min_application_amount', '<=', equivalent_sum),
                ('max_application_amount', '>=', equivalent_sum),
                ('contragent_zayavka_id', '=', False),
                ('agent_zayavka_id', '=', False),
                ('client_zayavka_id', '=', False),
                ('currency_zayavka', '=', False),
            ]

            rule = self.env[model].search(domain, limit=1)
            if not rule:
                _logger.info(f"[find_matching_rule] не найдена запись {model} для заявки {self.id}, ищем по общим условиям")
                rule = self.env[model].search(softDomain, limit=1)
                if not rule:
                    _logger.info(f"[find_matching_rule] не найдена запись {model} для заявки {self.id}, ищем по общим условиям")
                    return

            _logger.info(f"[find_matching_rule] найдена запись {rule.id} для заявки {self.id}")
            return rule

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
            # Сначала получаем все записи для детального анализа
            all_rules = self.env[model].search([])
            _logger.info(f"[RULE_AUTOMATION] Всего записей в модели {model}: {len(all_rules)}")
            
            if not all_rules:
                _logger.warning(f"[RULE_AUTOMATION] В модели {model} нет записей!")
                return None
            
            # Логируем все записи для анализа
            for rule in all_rules:
                _logger.info(f"[RULE_AUTOMATION] Запись {model} ID={rule.id}: {rule.name}")
                _logger.info(f"  Дата начала: {getattr(rule, date_field_start, 'НЕТ ПОЛЯ')}")
                _logger.info(f"  Дата конца: {getattr(rule, date_field_end, 'НЕТ ПОЛЯ')}")
                _logger.info(f"  Мин сумма: {getattr(rule, 'min_application_amount', 'НЕТ ПОЛЯ')}")
                _logger.info(f"  Макс сумма: {getattr(rule, 'max_application_amount', 'НЕТ ПОЛЯ')}")
                _logger.info(f"  Контрагент: {getattr(rule, 'contragent_zayavka_id', 'НЕТ ПОЛЯ')}")
                _logger.info(f"  Агент: {getattr(rule, 'agent_zayavka_id', 'НЕТ ПОЛЯ')}")
                _logger.info(f"  Клиент: {getattr(rule, 'client_zayavka_id', 'НЕТ ПОЛЯ')}")
                _logger.info(f"  Валюта: {getattr(rule, 'currency_zayavka', 'НЕТ ПОЛЯ')}")
                
                # Проверяем каждое условие отдельно
                date_start_ok = getattr(rule, date_field_start, None) and getattr(rule, date_field_start) <= rate_fixation_date
                date_end_ok = getattr(rule, date_field_end, None) and getattr(rule, date_field_end) >= rate_fixation_date
                min_amount_ok = getattr(rule, 'min_application_amount', None) is not None and getattr(rule, 'min_application_amount') <= equivalent_sum
                max_amount_ok = getattr(rule, 'max_application_amount', None) is not None and getattr(rule, 'max_application_amount') >= equivalent_sum
                
                _logger.info(f"  ✓ Проверка условий для записи {rule.id}:")
                _logger.info(f"    Дата начала ({getattr(rule, date_field_start, None)} <= {rate_fixation_date}): {'✓' if date_start_ok else '✗'}")
                _logger.info(f"    Дата конца ({getattr(rule, date_field_end, None)} >= {rate_fixation_date}): {'✓' if date_end_ok else '✗'}")
                _logger.info(f"    Мин сумма ({getattr(rule, 'min_application_amount', None)} <= {equivalent_sum}): {'✓' if min_amount_ok else '✗'}")
                _logger.info(f"    Макс сумма ({getattr(rule, 'max_application_amount', None)} >= {equivalent_sum}): {'✓' if max_amount_ok else '✗'}")
                
                # Проверяем дополнительные условия
                contragent_rule = getattr(rule, 'contragent_zayavka_id', None)
                agent_rule = getattr(rule, 'agent_zayavka_id', None)
                client_rule = getattr(rule, 'client_zayavka_id', None)
                currency_rule = getattr(rule, 'currency_zayavka', None)
                
                # ИСПРАВЛЕНА ЛОГИКА: пустое поле в правиле = подходит ЛЮБОЕ значение в заявке
                contragent_ok = (not contragent_rule) or (contragent_rule and contragent and contragent_rule.id == contragent.id)
                agent_ok = (not agent_rule) or (agent_rule and agent and agent_rule.id == agent.id)
                client_ok = (not client_rule) or (client_rule and client and client_rule.id == client.id)
                currency_ok = (not currency_rule) or (currency_rule and currency and currency_rule == currency)
                
                _logger.info(f"    Контрагент ({contragent_rule} vs {contragent}): {'✓' if contragent_ok else '✗'}")
                _logger.info(f"    Агент ({agent_rule} vs {agent}): {'✓' if agent_ok else '✗'}")
                _logger.info(f"    Клиент ({client_rule} vs {client}): {'✓' if client_ok else '✗'}")
                _logger.info(f"    Валюта ({currency_rule} vs {currency}): {'✓' if currency_ok else '✗'}")
                
                all_conditions_ok = date_start_ok and date_end_ok and min_amount_ok and max_amount_ok and contragent_ok and agent_ok and client_ok and currency_ok
                _logger.info(f"  🎯 Все условия выполнены: {'✓ ДА' if all_conditions_ok else '✗ НЕТ'}")
                _logger.info("  " + "-" * 50)

            domain = [
                (date_field_start, '<=', rate_fixation_date),
                (date_field_end, '>=', rate_fixation_date),
                ('min_application_amount', '<=', equivalent_sum),
                ('max_application_amount', '>=', equivalent_sum),
            ]
            
            # ИСПРАВЛЕНА ЛОГИКА ДОМЕНА: ищем правила ИЛИ с конкретным значением ИЛИ с пустым полем
            if contragent:
                domain.append('|')  # OR operator
                domain.append(('contragent_zayavka_id', '=', contragent.id))
                domain.append(('contragent_zayavka_id', '=', False))
            else:
                domain.append(('contragent_zayavka_id', '=', False))
                
            if agent:
                domain.append('|')  # OR operator
                domain.append(('agent_zayavka_id', '=', agent.id))
                domain.append(('agent_zayavka_id', '=', False))
            else:
                domain.append(('agent_zayavka_id', '=', False))
            
            if client:
                domain.append('|')  # OR operator
                domain.append(('client_zayavka_id', '=', client.id))
                domain.append(('client_zayavka_id', '=', False))
            else:
                domain.append(('client_zayavka_id', '=', False))

            if currency:
                domain.append('|')  # OR operator
                domain.append(('currency_zayavka', '=', currency))
                domain.append(('currency_zayavka', '=', False))
            else:
                domain.append(('currency_zayavka', '=', False))

            softDomain = [
                (date_field_start, '<=', rate_fixation_date),
                (date_field_end, '>=', rate_fixation_date),
                ('min_application_amount', '<=', equivalent_sum),
                ('max_application_amount', '>=', equivalent_sum),
                ('contragent_zayavka_id', '=', False),
                ('agent_zayavka_id', '=', False),
                ('client_zayavka_id', '=', False),
                ('currency_zayavka', '=', False),
            ]

            _logger.info(f"[RULE_AUTOMATION] Поиск в модели {model} с точным доменом: {domain}")
            rule = self.env[model].search(domain, limit=1)
            if not rule:
                _logger.info(f"[RULE_AUTOMATION] Не найдена запись {model} для заявки {self.id}, ищем по общим условиям")
                _logger.info(f"[RULE_AUTOMATION] Поиск в модели {model} с общим доменом: {softDomain}")
                rule = self.env[model].search(softDomain, limit=1)
                if not rule:
                    _logger.warning(f"[RULE_AUTOMATION] Не найдена запись {model} для заявки {self.id} даже по общим условиям")
                    return None

            _logger.info(f"[RULE_AUTOMATION] ✅ Найдена запись {model}: {rule.id} (название: {rule.name})")
            return rule

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
