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
                (date_field_end, '>=', deal_closed_date)
            ]
            
            # Добавляем условия по сумме заявки: min < equivalent_sum И max > equivalent_sum
            domain += [
                ('min_application_amount', '<=', equivalent_sum),
                ('max_application_amount', '>=', equivalent_sum),
            ]

            rule = self.env[model].search(domain, limit=1)
            _logger.info(f"[find_matching_rule] найдена запись {rule.name} для заявки {self.id}")
            _logger.info(f"[find_matching_rule] {rule}: rule_date_start = {rule.date_start}, rule_date_end = {rule.date_end} zayavka_date = {deal_closed_date}")
            _logger.info(f"[find_matching_rule] {rule}: min_application_amount = {rule.min_application_amount}, max_application_amount = {rule.max_application_amount} zayavka_amount = {equivalent_sum}")
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
