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
            
            if contragent:
                domain.append(('contragent_zayavka_id', 'in', [contragent.id]))
            else:
                domain.append(('contragent_zayavka_id', '=', False))
                
            if agent:
                domain.append(('agent_zayavka_id', 'in', [agent.id]))
            else:
                domain.append(('agent_zayavka_id', '=', False))
            
            if client:
                domain.append(('client_zayavka_id', 'in', [client.id]))
            else:
                domain.append(('client_zayavka_id', '=', False))

            if currency:
                domain.append(('currency_zayavka', 'in', [currency]))
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
