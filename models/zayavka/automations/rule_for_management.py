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

        # 4. Получаем дату
        deal_closed_date = self.deal_closed_date
        if not deal_closed_date:
            _logger.error(f'Поле "сделка закрыта" пустое у заявки {self.id}.')
            return

        # 5. Поиск подходящих записей
        def find_matching_rule(model, date_field_start, date_field_end):
            return self.env[model].search([
                (date_field_start, '<=', deal_closed_date),
                (date_field_end, '>=', deal_closed_date)
            ], limit=1)

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
