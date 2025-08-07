import logging
from odoo import models

_logger = logging.getLogger(__name__)

class ZayavkaReturnAutomations(models.Model):
    _inherit = 'amanat.zayavka'

    def run_return_with_main_amount(self): # ! Проверен
        if self.deal_type == 'export':
            return self._return_with_main_amount_method(isExport=True)
        else:
            return self._return_with_main_amount_method(isExport=False)
    
    def run_return_with_subsequent_payment_method(self): # ! Проверен
        if self.deal_type == 'export':
            self._return_with_subsequent_payment_method(isExport=True)
        else:
            self._return_with_subsequent_payment_method(isExport=False)
    
    def run_return_with_subsequent_payment_method_new_subagent(self, new_amount, date): # !
        if not self.subagent_ids:
            _logger.warning("Не заполнен Субагент!")
            return False
        
        if self.payers_for_return:
            new_subagent_payer = self.payers_for_return[0]
        else:
            subagent_payer = self._get_first_payer(self.subagent_ids[0])
            temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer
            new_subagent_payer = temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)

        if not new_amount:
            _logger.warning("Не передана сумма оплаты!")
            return False
        
        if self.deal_type == 'export':
            return self._return_with_subsequent_payment_method_new_subagent(isExport=True, new_subagent_payer=new_subagent_payer, new_amount=new_amount, date=date)
        else:
            return self._return_with_subsequent_payment_method_new_subagent(isExport=False, new_subagent_payer=new_subagent_payer, new_amount=new_amount, date=date)

    def run_return_with_all_amount_method(self): # ! Проверен
        if self.is_sberbank_contragent and not self.is_sovcombank_contragent:
            payment_cost = self.sber_payment_cost
        elif not self.is_sberbank_contragent and self.is_sovcombank_contragent:
            payment_cost = self.payment_cost_sovok
        else:
            payment_cost = self.client_payment_cost
        
        if self.deal_type == 'export':
            return self._return_with_all_amount_method(isExport=True, payment_cost=payment_cost)
        else:
            return self._return_with_all_amount_method(isExport=False, payment_cost=payment_cost)

    def run_return_with_partial_payment_of_remuneration_method(self): # ! Проверен
        if self.deal_type == 'export':
            return self._return_with_partial_payment_of_remuneration_method(isExport=True)
        else:
            return self._return_with_partial_payment_of_remuneration_method(isExport=False)

    def run_return_with_prepayment_of_next_method(self):
        if self.is_sberbank_contragent and not self.is_sovcombank_contragent:
            _logger.info(f"[_return_with_prepayment_of_next_method] self.sber_payment_cost: {self.sber_payment_cost}")
            payment_cost = self.sber_payment_cost
        elif not self.is_sberbank_contragent and self.is_sovcombank_contragent:
            _logger.info(f"[_return_with_prepayment_of_next_method] self.payment_cost_sovok: {self.payment_cost_sovok}")
            payment_cost = self.payment_cost_sovok
        else:
            _logger.info(f"[_return_with_prepayment_of_next_method] self.client_payment_cost: {self.client_payment_cost}")
            payment_cost = self.client_payment_cost
        
        _logger.info(f"[_return_with_prepayment_of_next_method] payment_cost: {payment_cost}")

        if self.deal_type == 'export':
            return self._return_with_prepayment_of_next_method(isExport=True, payment_cost=payment_cost)
        else:
            return self._return_with_prepayment_of_next_method(isExport=False, payment_cost=payment_cost)

    def _return_with_all_amount_method(self, payment_cost, isExport = False): # ! Проверен
        _logger.info("[_return_with_all_amount_method] Создаем ордер/контейнера/сверки...")
        date = self.payment_order_date_to_client_account_return_all

        if not payment_cost:
            _logger.warning("[_return_with_all_amount_method] Сумма вознаграждения не была передена в метод!")
            return False
        
        agent = self.agent_id
        if not agent:
            _logger.warning("[_return_with_all_amount_method] Не заполнен Агент!")
            return False
        
        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("[_return_with_all_amount_method] Не заполнен Плательщик Агента!")
            return False
        
        if not self.subagent_ids:
            _logger.warning("[_return_with_all_amount_method] Не заполнен Субагент!")
            return False
        subagent = self.subagent_ids[0]
        
        subagent_payer = self._get_first_payer(subagent)
        if not subagent_payer:
            _logger.warning("[_return_with_all_amount_method] Не заполнен Плательщик Субагента!")
            return False

        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer

        currency = self.currency
        agentka_wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("[_return_with_all_amount_method] Кошелек 'Агентка' не найден.")
            return False
        
        amount = self.amount
        if not amount:
            _logger.warning("[_return_with_all_amount_method] Сумма заявки не заполнена!")
            return False

        return_amount = self.return_amount
        if not return_amount:
            _logger.warning("[_return_with_all_amount_method] Сумма возврата не заполнена!")
            return False

        client = self.client_id
        if not client:
            _logger.warning("[_return_with_all_amount_method] Не заполнен Клиент!")
            return False
        
        client_payer = self._get_first_payer(client)
        if not client_payer:
            _logger.warning("[_return_with_all_amount_method] Не заполнен Плательщик Клиента!")
            return False

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("[_return_with_all_amount_method] Не заполнен Контрагент!")
            return False

        zayavka_id = self.id

        order = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id if isExport else agent.id,
            'payer_1_id': (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id,
            'partner_2_id': agent.id if isExport else subagent.id,
            'payer_2_id': agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)),
            'amount': amount,
            'currency': currency,
            'wallet_1_id': agentka_wallet.id,
            'wallet_2_id': agentka_wallet.id,
            'zayavka_ids': [(6, 0, [zayavka_id])],
            'comment': f"Возврат валюты по {self.zayavka_num}",
        })
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt' if isExport else 'positive',
            'wallet_id': agentka_wallet.id,
            'order_id': order.id,
            **self._get_currency_fields(currency, -amount if isExport else amount),
        })
        self._create_reconciliation({
            'date': date,
            'currency': currency,
            **self._get_reconciliation_currency_fields(currency, -amount if isExport else amount),
            'partner_id': subagent.id if isExport else agent.id,
            'order_id': [(6, 0, [order.id])],
            'sender_id': [(6, 0, [(temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id])],
            'receiver_id': [(6, 0, [agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False))])],
            'wallet_id': agentka_wallet.id,
        })

        order2 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id if isExport else agent.id,
            'payer_1_id': (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id,
            'partner_2_id': agent.id if isExport else subagent.id,
            'payer_2_id': agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)),
            'amount': payment_cost,
            'currency': currency,
            'wallet_1_id': agentka_wallet.id,
            'wallet_2_id': agentka_wallet.id,
            'zayavka_ids': [(6, 0, [zayavka_id])],
            'comment': f"Возврат вознаграждения субагента за провод платежа по заявке {self.zayavka_num}",
        })
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt' if isExport else 'positive',
            'wallet_id': agentka_wallet.id,
            'order_id': order2.id,
            **self._get_currency_fields(currency, -payment_cost if isExport else payment_cost),
        })
        self._create_reconciliation({
            'date': date,
            'currency': currency,
            **self._get_reconciliation_currency_fields(currency, -payment_cost if isExport else payment_cost),
            'partner_id': subagent.id,
            'order_id': [(6, 0, [order2.id])],
            'sender_id': [(6, 0, [(temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id])],
            'receiver_id': [(6, 0, [agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False))])],
            'wallet_id': agentka_wallet.id,
        })

        for extract in self.extract_delivery_ids:
            _logger.info(f"Обрабатываем выписку {extract.id}: сумма={extract.amount}")

            vypiska_payer = extract.payer
            vypiska_receiver = extract.recipient
            
            contragent_for_payer = vypiska_payer.contragents_ids[0] if vypiska_payer and vypiska_payer.contragents_ids else None
            contragent_for_receiver = vypiska_receiver.contragents_ids[0] if vypiska_receiver and vypiska_receiver.contragents_ids else None

            # Создаем ордер для этой выписки
            order_vals = {
                'date': date,
                'type': 'transfer',
                'partner_1_id': contragent_for_payer.id if contragent_for_payer else False,
                'partner_2_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'payer_1_id': vypiska_payer.id if vypiska_payer else False,
                'payer_2_id': vypiska_receiver.id if vypiska_receiver else False,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'currency': 'rub',
                'amount': return_amount,
                'comment': f'оплата рублей по заявке № {self.zayavka_num} (выписка {extract.id})',
                'zayavka_ids': [(6, 0, [zayavka_id])],
            }
            order = self._create_order(order_vals)

            # Создаем контейнеры (money) для отправителя (положительная сумма)
            money_vals_1 = {
                'date': date,
                'partner_id': contragent_for_payer.id if contragent_for_payer else False,
                'currency': 'rub',
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order.id,
                **self._get_currency_fields('rub', return_amount)
            }
            self._create_money(money_vals_1)

            # Создаем контейнеры (money) для получателя (отрицательная сумма)
            money_vals_2 = {
                'date': date,
                'partner_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'currency': 'rub',
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order.id,
                **self._get_currency_fields('rub', -return_amount)
            }
            self._create_money(money_vals_2)

            # Создаем сверку для отправителя (положительная сумма)
            reconciliation_vals_1 = {
                'date': date,
                'partner_id': contragent_for_payer.id if contragent_for_payer else False,
                'currency': 'rub',
                'sum': -return_amount,
                'wallet_id': agentka_wallet.id,
                'order_id': [(4, order.id)],  # Many2many поле
                **self._get_reconciliation_currency_fields('rub', return_amount)
            }
            # Добавляем sender_id и receiver_id если они есть
            if vypiska_payer:
                reconciliation_vals_1['sender_id'] = [(4, vypiska_payer.id)]
            if vypiska_receiver:
                reconciliation_vals_1['receiver_id'] = [(4, vypiska_receiver.id)]
            
            self._create_reconciliation(reconciliation_vals_1)

            # Создаем сверку для получателя (отрицательная сумма)
            reconciliation_vals_2 = {
                'date': date,
                'partner_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'currency': 'rub',
                'sum': return_amount,
                'wallet_id': agentka_wallet.id,
                'order_id': [(4, order.id)],  # Many2many поле
                **self._get_reconciliation_currency_fields('rub', -return_amount)
            }
            # Добавляем sender_id и receiver_id если они есть
            if vypiska_payer:
                reconciliation_vals_2['sender_id'] = [(4, vypiska_payer.id)]
            if vypiska_receiver:
                reconciliation_vals_2['receiver_id'] = [(4, vypiska_receiver.id)]
                
            self._create_reconciliation(reconciliation_vals_2)

        return True

    def _return_with_main_amount_method(self, isExport = False): # ! Проверен
        _logger.info("[_return_with_main_amount_method] Создаем ордер/контейнера/сверки...")
        date = self.payment_order_date_to_client_account

        agent = self.agent_id
        if not agent:
            _logger.warning("[_return_with_main_amount_method] Не заполнен Агент!")
            return False
        
        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("[_return_with_main_amount_method] Не заполнен Плательщик Агента!")
            return False
        
        if not self.subagent_ids:
            _logger.warning("[_return_with_main_amount_method] Не заполнен Субагент!")
            return False
        subagent = self.subagent_ids[0]
        
        subagent_payer = self._get_first_payer(subagent)
        if not subagent_payer:
            _logger.warning("[_return_with_main_amount_method] Не заполнен Плательщик Субагента!")
            return False

        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer

        currency = self.currency
        if not currency:
            _logger.warning("[_return_with_main_amount_method] Не заполнен Валюта!")
            return False
        
        agentka_wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("[_return_with_main_amount_method] Кошелек 'Агентка' не найден.")
            return False
        
        amount = self.amount
        if not amount:
            _logger.warning("[_return_with_main_amount_method] Сумма заявки не заполнена!")
            return False

        return_amount = self.return_amount_to_client
        if not return_amount:
            _logger.warning("[_return_with_main_amount_method] Сумма возврата не заполнена!")
            return False

        client = self.client_id
        if not client:
            _logger.warning("[_return_with_main_amount_method] Не заполнен Клиент!")
            return False
        
        client_payer = self._get_first_payer(client)
        if not client_payer:
            _logger.warning("[_return_with_main_amount_method] Не заполнен Плательщик Клиента!")
            return False

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("[_return_with_main_amount_method] Не заполнен Контрагент!")
            return False

        zayavka_id = self.id

        order = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id if isExport else agent.id,
            'payer_1_id': (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id,
            'partner_2_id': agent.id if isExport else subagent.id,
            'payer_2_id': agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)),
            'amount': amount,
            'currency': currency,
            'wallet_1_id': agentka_wallet.id,
            'wallet_2_id': agentka_wallet.id,
            'zayavka_ids': [(6, 0, [zayavka_id])],
            'comment': f"Возврат валюты по {self.zayavka_num}",
        })
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt' if isExport else 'positive',
            'wallet_id': agentka_wallet.id,
            'order_id': order.id,
            **self._get_currency_fields(currency, -amount if isExport else amount),
        })
        self._create_reconciliation({
            'date': date,
            'currency': currency,
            **self._get_reconciliation_currency_fields(currency, -amount if isExport else amount),
            'partner_id': subagent.id if isExport else agent.id,
            'order_id': [(6, 0, [order.id])],
            'sender_id': [(6, 0, [(temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id])],
            'receiver_id': [(6, 0, [agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False))])],
            'wallet_id': agentka_wallet.id,
        })

        for extract in self.extract_delivery_ids:
            _logger.info(f"Обрабатываем выписку {extract.id}: сумма={extract.amount}")

            vypiska_payer = extract.payer
            vypiska_receiver = extract.recipient
            
            contragent_for_payer = vypiska_payer.contragents_ids[0] if vypiska_payer and vypiska_payer.contragents_ids else None
            contragent_for_receiver = vypiska_receiver.contragents_ids[0] if vypiska_receiver and vypiska_receiver.contragents_ids else None

            # Создаем ордер для этой выписки
            order_vals = {
                'date': date,
                'type': 'transfer',
                'partner_1_id': contragent_for_payer.id if contragent_for_payer else False,
                'partner_2_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'payer_1_id': vypiska_payer.id if vypiska_payer else False,
                'payer_2_id': vypiska_receiver.id if vypiska_receiver else False,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'currency': 'rub',
                'amount': return_amount,
                'comment': f'оплата рублей по заявке № {self.zayavka_num} (выписка {extract.id})',
                'zayavka_ids': [(6, 0, [zayavka_id])],
            }
            order = self._create_order(order_vals)

            # Создаем контейнеры (money) для отправителя (положительная сумма)
            money_vals_1 = {
                'date': date,
                'partner_id': contragent_for_payer.id if contragent_for_payer else False,
                'currency': 'rub',
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order.id,
                **self._get_currency_fields('rub', return_amount)
            }
            self._create_money(money_vals_1)

            # Создаем контейнеры (money) для получателя (отрицательная сумма)
            money_vals_2 = {
                'date': date,
                'partner_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'currency': 'rub',
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order.id,
                **self._get_currency_fields('rub', -return_amount)
            }
            self._create_money(money_vals_2)

            # Создаем сверку для отправителя (положительная сумма)
            reconciliation_vals_1 = {
                'date': date,
                'partner_id': contragent_for_payer.id if contragent_for_payer else False,
                'currency': 'rub',
                'sum': -return_amount,
                'wallet_id': agentka_wallet.id,
                'order_id': [(4, order.id)],  # Many2many поле
                **self._get_reconciliation_currency_fields('rub', return_amount)
            }
            # Добавляем sender_id и receiver_id если они есть
            if vypiska_payer:
                reconciliation_vals_1['sender_id'] = [(4, vypiska_payer.id)]
            if vypiska_receiver:
                reconciliation_vals_1['receiver_id'] = [(4, vypiska_receiver.id)]
            
            self._create_reconciliation(reconciliation_vals_1)

            # Создаем сверку для получателя (отрицательная сумма)
            reconciliation_vals_2 = {
                'date': date,
                'partner_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'currency': 'rub',
                'sum': return_amount,
                'wallet_id': agentka_wallet.id,
                'order_id': [(4, order.id)],  # Many2many поле
                **self._get_reconciliation_currency_fields('rub', -return_amount)
            }
            # Добавляем sender_id и receiver_id если они есть
            if vypiska_payer:
                reconciliation_vals_2['sender_id'] = [(4, vypiska_payer.id)]
            if vypiska_receiver:
                reconciliation_vals_2['receiver_id'] = [(4, vypiska_receiver.id)]
                
            self._create_reconciliation(reconciliation_vals_2)

        return True
    
    def _return_with_partial_payment_of_remuneration_method(self, isExport = False): # ! Проверен
        _logger.info("[_return_with_partial_payment_of_remuneration_method] Создаем ордер/контейнера/сверки...")
        date = self.payment_order_date_to_return

        payment_cost = self.return_amount_to_reward
        if not payment_cost:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Сумма вознаграждения не была передена в метод!")
            return False

        agent = self.agent_id
        if not agent:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Не заполнен Агент!")
            return False
        
        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Не заполнен Плательщик Агента!")
            return False
        
        if not self.subagent_ids:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Не заполнен Субагент!")
            return False
        subagent = self.subagent_ids[0]
        
        subagent_payer = self._get_first_payer(subagent)
        if not subagent_payer:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Не заполнен Плательщик Субагента!")
            return False

        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer

        currency = self.currency
        if not currency:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Не заполнен Валюта!")
            return False
        
        agentka_wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Кошелек 'Агентка' не найден.")
            return False
        
        amount = self.amount
        if not amount:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Сумма заявки не заполнена!")
            return False

        return_amount = self.return_amount_main
        if not return_amount:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Сумма возврата не заполнена!")
            return False

        client = self.client_id
        if not client:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Не заполнен Клиент!")
            return False
        
        client_payer = self._get_first_payer(client)
        if not client_payer:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Не заполнен Плательщик Клиента!")
            return False

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("[_return_with_partial_payment_of_remuneration_method] Не заполнен Контрагент!")
            return False

        zayavka_id = self.id

        order = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id if isExport else agent.id,
            'payer_1_id': (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id,
            'partner_2_id': agent.id if isExport else subagent.id,
            'payer_2_id': agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)),
            'amount': amount,
            'currency': currency,
            'wallet_1_id': agentka_wallet.id,
            'wallet_2_id': agentka_wallet.id,
            'zayavka_ids': [(6, 0, [zayavka_id])],
            'comment': f"Возврат валюты по {self.zayavka_num}",
        })
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt' if isExport else 'positive',
            'wallet_id': agentka_wallet.id,
            'order_id': order.id,
            **self._get_currency_fields(currency, -amount if isExport else amount),
        })
        self._create_reconciliation({
            'date': date,
            'currency': currency,
            **self._get_reconciliation_currency_fields(currency, -amount if isExport else amount),
            'partner_id': subagent.id if isExport else agent.id,
            'order_id': [(6, 0, [order.id])],
            'sender_id': [(6, 0, [(temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id])],
            'receiver_id': [(6, 0, [agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False))])],
            'wallet_id': agentka_wallet.id,
        })

        order2 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id if isExport else agent.id,
            'payer_1_id': (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id,
            'partner_2_id': agent.id if isExport else subagent.id,
            'payer_2_id': agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)),
            'amount': payment_cost,
            'currency': currency,
            'wallet_1_id': agentka_wallet.id,
            'wallet_2_id': agentka_wallet.id,
            'zayavka_ids': [(6, 0, [zayavka_id])],
            'comment': f"Возврат вознаграждения субагента за провод платежа по заявке {self.zayavka_num}",
        })
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt' if isExport else 'positive',
            'wallet_id': agentka_wallet.id,
            'order_id': order2.id,
            **self._get_currency_fields(currency, -payment_cost if isExport else payment_cost),
        })
        self._create_reconciliation({
            'date': date,
            'currency': currency,
            **self._get_reconciliation_currency_fields(currency, -payment_cost if isExport else payment_cost),
            'partner_id': subagent.id,
            'order_id': [(6, 0, [order2.id])],
            'sender_id': [(6, 0, [(temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id])],
            'receiver_id': [(6, 0, [agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False))])],
            'wallet_id': agentka_wallet.id,
        })

        for extract in self.extract_delivery_ids:
            _logger.info(f"Обрабатываем выписку {extract.id}: сумма={extract.amount}")

            vypiska_payer = extract.payer
            vypiska_receiver = extract.recipient
            
            contragent_for_payer = vypiska_payer.contragents_ids[0] if vypiska_payer and vypiska_payer.contragents_ids else None
            contragent_for_receiver = vypiska_receiver.contragents_ids[0] if vypiska_receiver and vypiska_receiver.contragents_ids else None

            # Создаем ордер для этой выписки
            order_vals = {
                'date': date,
                'type': 'transfer',
                'partner_1_id': contragent_for_payer.id if contragent_for_payer else False,
                'partner_2_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'payer_1_id': vypiska_payer.id if vypiska_payer else False,
                'payer_2_id': vypiska_receiver.id if vypiska_receiver else False,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'currency': 'rub',
                'amount': return_amount,
                'comment': f'оплата рублей по заявке № {self.zayavka_num} (выписка {extract.id})',
                'zayavka_ids': [(6, 0, [zayavka_id])],
            }
            order = self._create_order(order_vals)

            # Создаем контейнеры (money) для отправителя (положительная сумма)
            money_vals_1 = {
                'date': date,
                'partner_id': contragent_for_payer.id if contragent_for_payer else False,
                'currency': 'rub',
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order.id,
                **self._get_currency_fields('rub', return_amount)
            }
            self._create_money(money_vals_1)

            # Создаем контейнеры (money) для получателя (отрицательная сумма)
            money_vals_2 = {
                'date': date,
                'partner_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'currency': 'rub',
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order.id,
                **self._get_currency_fields('rub', -return_amount)
            }
            self._create_money(money_vals_2)

            # Создаем сверку для отправителя (положительная сумма)
            reconciliation_vals_1 = {
                'date': date,
                'partner_id': contragent_for_payer.id if contragent_for_payer else False,
                'currency': 'rub',
                'sum': -return_amount,
                'wallet_id': agentka_wallet.id,
                'order_id': [(4, order.id)],  # Many2many поле
                **self._get_reconciliation_currency_fields('rub', return_amount)
            }
            # Добавляем sender_id и receiver_id если они есть
            if vypiska_payer:
                reconciliation_vals_1['sender_id'] = [(4, vypiska_payer.id)]
            if vypiska_receiver:
                reconciliation_vals_1['receiver_id'] = [(4, vypiska_receiver.id)]
            
            self._create_reconciliation(reconciliation_vals_1)

            # Создаем сверку для получателя (отрицательная сумма)
            reconciliation_vals_2 = {
                'date': date,
                'partner_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'currency': 'rub',
                'sum': return_amount,
                'wallet_id': agentka_wallet.id,
                'order_id': [(4, order.id)],  # Many2many поле
                **self._get_reconciliation_currency_fields('rub', -return_amount)
            }
            # Добавляем sender_id и receiver_id если они есть
            if vypiska_payer:
                reconciliation_vals_2['sender_id'] = [(4, vypiska_payer.id)]
            if vypiska_receiver:
                reconciliation_vals_2['receiver_id'] = [(4, vypiska_receiver.id)]
                
            self._create_reconciliation(reconciliation_vals_2)

        return True

    def _return_with_subsequent_payment_method(self, isExport = False): # ! Проверен
        _logger.info("[_return_with_subsequent_payment_method] Создаем ордер/контейнера/сверки...")
        date = self.payment_date_again_1
        if not date:
            _logger.warning("Дата оплаты валюты поставщику не заполнена!")
            return False

        agent = self.agent_id
        if not agent:
            _logger.warning("[_return_with_subsequent_payment_method] Не заполнен Агент!")
            return False
        
        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("[_return_with_subsequent_payment_method] Не заполнен Плательщик Агента!")
            return False
        
        if not self.subagent_ids:
            _logger.warning("[_return_with_subsequent_payment_method] Не заполнен Субагент!")
            return False
        subagent = self.subagent_ids[0]
        
        subagent_payer = self._get_first_payer(subagent)
        if not subagent_payer:
            _logger.warning("[_return_with_subsequent_payment_method] Не заполнен Плательщик Субагента!")
            return False

        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer

        currency = self.currency
        if not currency:
            _logger.warning("[_return_with_subsequent_payment_method] Не заполнен Валюта!")
            return False
        
        agentka_wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("[_return_with_subsequent_payment_method] Кошелек 'Агентка' не найден.")
            return False
        
        amount = self.amount
        if not amount:
            _logger.warning("[_return_with_subsequent_payment_method] Сумма заявки не заполнена!")
            return False

        client = self.client_id
        if not client:
            _logger.warning("[_return_with_subsequent_payment_method] Не заполнен Клиент!")
            return False
        
        client_payer = self._get_first_payer(client)
        if not client_payer:
            _logger.warning("[_return_with_subsequent_payment_method] Не заполнен Плательщик Клиента!")
            return False

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("[_return_with_subsequent_payment_method] Не заполнен Контрагент!")
            return False

        zayavka_id = self.id

        order = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id if isExport else agent.id,
            'payer_1_id': (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id,
            'partner_2_id': agent.id if isExport else subagent.id,
            'payer_2_id': agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)),
            'amount': amount,
            'currency': currency,
            'wallet_1_id': agentka_wallet.id,
            'wallet_2_id': agentka_wallet.id,
            'zayavka_ids': [(6, 0, [zayavka_id])],
            'comment': f"Возврат валюты по {self.zayavka_num}",
        })
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt' if isExport else 'positive',
            'wallet_id': agentka_wallet.id,
            'order_id': order.id,
            **self._get_currency_fields(currency, -amount if isExport else amount),
        })
        self._create_reconciliation({
            'date': date,
            'currency': currency,
            **self._get_reconciliation_currency_fields(currency, -amount if isExport else amount),
            'partner_id': subagent.id if isExport else agent.id,
            'order_id': [(6, 0, [order.id])],
            'sender_id': [(6, 0, [(temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id])],
            'receiver_id': [(6, 0, [agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False))])],
            'wallet_id': agentka_wallet.id,
        })

        return True

    def _return_with_subsequent_payment_method_new_subagent(self, new_subagent_payer, new_amount, date, isExport = False): # ! Проверен
        _logger.info("[_return_with_subsequent_payment_method_new_subagent] Создаем ордер/контейнера/сверки...")
        if not date:
            _logger.warning("Дата оплаты валюты поставщику не заполнена!")
            return False

        if not new_subagent_payer:
            _logger.warning("[_return_with_subsequent_payment_method_new_subagent] Не передан Плательщик Субагента!")
            return False
        
        if not new_amount:
            _logger.warning("[_return_with_subsequent_payment_method_new_subagent] Не передана сумма оплаты!")
            return False

        agent = self.agent_id
        if not agent:
            _logger.warning("[_return_with_subsequent_payment_method_new_subagent] Не заполнен Агент!")
            return False
        
        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("[_return_with_subsequent_payment_method_new_subagent] Не заполнен Плательщик Агента!")
            return False
        
        if not self.subagent_ids:
            _logger.warning("[_return_with_subsequent_payment_method_new_subagent] Не заполнен Субагент!")
            return False
        subagent = self.subagent_ids[0]
        
        subagent_payer = new_subagent_payer

        currency = self.currency
        agentka_wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("[_return_with_subsequent_payment_method_new_subagent] Кошелек 'Агентка' не найден.")
            return False
        
        amount = new_amount

        client = self.client_id
        if not client:
            _logger.warning("[_return_with_subsequent_payment_method_new_subagent] Не заполнен Клиент!")
            return False
        
        client_payer = self._get_first_payer(client)
        if not client_payer:
            _logger.warning("[_return_with_subsequent_payment_method_new_subagent] Не заполнен Плательщик Клиента!")
            return False

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("[_return_with_subsequent_payment_method_new_subagent] Не заполнен Контрагент!")
            return False

        zayavka_id = self.id

        order = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id if isExport else agent.id,
            'payer_1_id': subagent_payer.id if isExport else agent_payer.id,
            'partner_2_id': agent.id if isExport else subagent.id,
            'payer_2_id': agent_payer.id if isExport else subagent_payer.id,
            'amount': amount,
            'currency': currency,
            'wallet_1_id': agentka_wallet.id,
            'wallet_2_id': agentka_wallet.id,
            'zayavka_ids': [(6, 0, [zayavka_id])],
            'comment': f"Оплата валюты по заявке {self.zayavka_num}",
        })
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt' if isExport else 'positive',
            'wallet_id': agentka_wallet.id,
            'order_id': order.id,
            **self._get_currency_fields(currency, -amount if isExport else amount),
        })
        self._create_reconciliation({
            'date': date,
            'currency': currency,
            **self._get_reconciliation_currency_fields(currency, -amount if isExport else amount),
            'partner_id': subagent.id if isExport else agent.id,
            'order_id': [(6, 0, [order.id])],
            'sender_id': [(6, 0, [subagent_payer.id if isExport else agent_payer.id])],
            'receiver_id': [(6, 0, [agent_payer.id if isExport else subagent_payer.id])],
            'wallet_id': agentka_wallet.id,
        })

        return True

    def _return_with_prepayment_of_next_method(self, payment_cost, isExport = False):
        _logger.info("[_return_with_prepayment_of_next_method] Создаем ордер/контейнера/сверки...")
        date = self.payment_order_date_to_prepayment_of_next
        
        if not payment_cost:
            _logger.warning(f"[_return_with_prepayment_of_next_method] Сумма вознаграждения не была передена в метод! payment_cost: {payment_cost}")
            return False

        agent = self.agent_id
        if not agent:
            _logger.warning("[_return_with_prepayment_of_next_method] Не заполнен Агент!")
            return False
        
        agent_payer = self._get_first_payer(agent)
        if not agent_payer:
            _logger.warning("[_return_with_prepayment_of_next_method] Не заполнен Плательщик Агента!")
            return False
        
        if not self.subagent_ids:
            _logger.warning("[_return_with_prepayment_of_next_method] Не заполнен Субагент!")
            return False
        subagent = self.subagent_ids[0]
        
        subagent_payer = self._get_first_payer(subagent)
        if not subagent_payer:
            _logger.warning("[_return_with_prepayment_of_next_method] Не заполнен Плательщик Субагента!")
            return False

        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer

        currency = self.currency
        if not currency:
            _logger.warning("[_return_with_prepayment_of_next_method] Не заполнен Валюта!")
            return False
        
        agentka_wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("[_return_with_prepayment_of_next_method] Кошелек 'Агентка' не найден.")
            return False
        
        return_amount = self.return_amount_prepayment_of_next
        if not return_amount:
            _logger.warning("[_return_with_prepayment_of_next_method] Сумма возврата не заполнена!")
            return False

        client = self.client_id
        if not client:
            _logger.warning("[_return_with_prepayment_of_next_method] Не заполнен Клиент!")
            return False
        
        client_payer = self._get_first_payer(client)
        if not client_payer:
            _logger.warning("[_return_with_prepayment_of_next_method] Не заполнен Плательщик Клиента!")
            return False

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("[_return_with_prepayment_of_next_method] Не заполнен Контрагент!")
            return False

        zayavka_id = self.id

        order = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id if isExport else agent.id,
            'payer_1_id': (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id,
            'partner_2_id': agent.id if isExport else subagent.id,
            'payer_2_id': agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)),
            'amount': return_amount,
            'currency': currency,
            'wallet_1_id': agentka_wallet.id,
            'wallet_2_id': agentka_wallet.id,
            'zayavka_ids': [(6, 0, [zayavka_id])],
            'comment': f"Возврат валюты по {self.zayavka_num}",
        })
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt' if isExport else 'positive',
            'wallet_id': agentka_wallet.id,
            'order_id': order.id,
            **self._get_currency_fields(currency, -return_amount if isExport else return_amount),
        })
        self._create_reconciliation({
            'date': date,
            'currency': currency,
            **self._get_reconciliation_currency_fields(currency, -return_amount if isExport else return_amount),
            'partner_id': subagent.id if isExport else agent.id,
            'order_id': [(6, 0, [order.id])],
            'sender_id': [(6, 0, [(temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id])],
            'receiver_id': [(6, 0, [agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False))])],
            'wallet_id': agentka_wallet.id,
        })

        order2 = self._create_order({
            'date': date,
            'type': 'transfer',
            'partner_1_id': subagent.id if isExport else agent.id,
            'payer_1_id': (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id,
            'partner_2_id': agent.id if isExport else subagent.id,
            'payer_2_id': agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)),
            'amount': payment_cost,
            'currency': currency,
            'wallet_1_id': agentka_wallet.id,
            'wallet_2_id': agentka_wallet.id,
            'zayavka_ids': [(6, 0, [zayavka_id])],
            'comment': f"Возврат вознаграждения субагента за провод платежа по заявке {self.zayavka_num}",
        })
        self._create_money({
            'date': date,
            'partner_id': subagent.id,
            'currency': currency,
            'state': 'debt' if isExport else 'positive',
            'wallet_id': agentka_wallet.id,
            'order_id': order2.id,
            **self._get_currency_fields(currency, -payment_cost if isExport else payment_cost),
        })
        self._create_reconciliation({
            'date': date,
            'currency': currency,
            **self._get_reconciliation_currency_fields(currency, -payment_cost if isExport else payment_cost),
            'partner_id': subagent.id,
            'order_id': [(6, 0, [order2.id])],
            'sender_id': [(6, 0, [(temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False)) if isExport else agent_payer.id])],
            'receiver_id': [(6, 0, [agent_payer.id if isExport else (temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False))])],
            'wallet_id': agentka_wallet.id,
        })

        return True