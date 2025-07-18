import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class ZayavkaFinEntryAutomations(models.Model):
    _inherit = 'amanat.zayavka'

    @api.model
    def run_all_fin_entry_automations(self):
        if self.is_sberbank_contragent and not self.is_sovcombank_contragent:
            if self.deal_type != "export":
                _logger.info("[ФИН ВХОД ЗАЯВКИ] Считаем как Сбербанк; Вид сделки: импорт")
                self._run_fin_entry_automation_sber_import()
            else:
                _logger.info("[ФИН ВХОД ЗАЯВКИ] Считаем как Сбербанк; Вид сделки: экспорт")
                self._run_fin_entry_automation_sber_export()
        elif self.is_sovcombank_contragent and not self.is_sberbank_contragent:
            if self.deal_type != "export":
                _logger.info("[ФИН ВХОД ЗАЯВКИ] Считаем как Совкомбанк; Вид сделки: импорт")
                self._run_fin_entry_automation_sovok_import()
            else:
                _logger.info("[ФИН ВХОД ЗАЯВКИ] Считаем как Совкомбанк; Вид сделки: экспорт")
                self._run_fin_entry_automation_sovok_export()
        else:
            if self.deal_type != "export":
                _logger.info("[ФИН ВХОД ЗАЯВКИ] Считаем как Клиент (Индивидуальная); Вид сделки: импорт")
                self._run_fin_entry_automation_client_import()
            else:
                _logger.info("[ФИН ВХОД ЗАЯВКИ] Считаем как Клиент (Индивидуальная); Вид сделки: экспорт")
                self._run_fin_entry_automation_client_export()

    @api.model
    def _run_fin_entry_automation_sovok_import(self):
        wallet_model         = self.env['amanat.wallet']         # Кошельки

        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        # Филтруем по условию: Контрагент "Совкомбанк" и вид сделки "Импорт"
        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return

        # Удаляем старые ордера, сверки и контейнеры
        self._clear_related_documents()

        date = self.supplier_currency_paid_date
        if not date:
            _logger.warning("Не заполнена дата оплаты поставщику!")
            return
        
        _logger.info(f"Установлена дата: {date}")
        
        agent = self.agent_id
        if not agent:
            _logger.warning("Не заполнен агент!")
            return

        if not self.subagent_ids:
            _logger.warning("Не заполнен субагент!")
            return
        
        subagent = self.subagent_ids[0]

        client = self.client_id
        if not client:
            _logger.warning("Не заполнен клиент!")
            return
        
        currency = self.currency
        if not currency:
            _logger.warning("Не заполнена валюта!")
            return

        amount = self.amount
        
        payment_cost_sovok = self.payment_cost_sovok
        
        our_sovok_reward = self.our_sovok_reward
        
        best_rate = self.best_rate
        if not best_rate:
            _logger.warning("Не заполнена лучшая ставка!")
            return
        
        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Не заполнен Номер заявки!")
            return
        
        if not self.subagent_payer_ids:
            _logger.warning("Не заполнен Плательщик субагента!")
            return

        agentka_wallet = wallet_model.search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        subagent_payer = self._get_first_payer(subagent)
        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer
        
        # --- Order 1
        if amount:
            order1 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Формируем долг в валюте на Сумма заявки по заявке {record_id} для конвертации",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order1.id,
                **self._get_currency_fields(currency, amount)
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'order_id': [(6, 0, [order1.id])],
                'partner_id': contragent.id,
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 1")

        # --- Order 2
        if amount:
            order2 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount,
                'rate': best_rate,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Проводим конвертацию Суммы заявки по курсу {best_rate} в рубли по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order2.id,
                **self._get_currency_fields(currency, -amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order2.id])],
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
            amount_in_rub = amount * best_rate
            if amount_in_rub:
                self._create_money({
                    'date': date,
                    'partner_id': client.id,
                    'currency': 'rub',
                    'state': 'positive',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order2.id,
                    **self._get_currency_fields('rub', amount_in_rub),
                })
                self._create_reconciliation({
                    'date': date,
                    'currency': 'rub',
                    **self._get_reconciliation_currency_fields('rub', amount_in_rub),
                    'partner_id': contragent.id,
                    'order_id': [(6, 0, [order2.id])],
                    'sender_id': [(6, 0, [client_payer.id])],
                    'receiver_id': [(6, 0, [agent_payer.id])],
                    'wallet_id': agentka_wallet.id,
                })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 2")

        # --- Order 3
        if our_sovok_reward:
            order3 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': our_sovok_reward,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order3.id,
                **self._get_currency_fields('rub', our_sovok_reward),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', our_sovok_reward),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order3.id])],
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не заполнена, не создаем ордер 3")
            
        # --- Order 5
        if amount:
            order5 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': subagent.id,
                'payer_2_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата валюты по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order5.id,
                **self._get_currency_fields(currency, -amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order5.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты валюты не заполнена, не создаем ордер 5")
            
        # --- Order 6
        if payment_cost_sovok:
            order6 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': subagent.id,
                'payer_2_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'amount': payment_cost_sovok,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата вознаграждения субагента за провод платежа по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order6.id,
                **self._get_currency_fields(currency, -payment_cost_sovok),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -payment_cost_sovok),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order6.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты вознаграждения субагента не заполнена, не создаем ордер 6")

    @api.model
    def _run_fin_entry_automation_sber_import(self):
        wallet_model         = self.env['amanat.wallet']         # Кошельки

        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return

        # Удаляем старые ордера, сверки и контейнеры
        self._clear_related_documents()

        date = self.supplier_currency_paid_date
        if not date:
            _logger.warning("Не заполнена дата оплаты поставщику!")
            return
        
        _logger.info(f"Установлена дата: {date}")
        
        agent = self.agent_id
        if not agent:
            _logger.warning("Не заполнен агент!")
            return

        if not self.subagent_ids:
            _logger.warning("Не заполнен субагент!")
            return
        
        subagent = self.subagent_ids[0]

        client = self.client_id
        if not client:
            _logger.warning("Не заполнен клиент!")
            return
        
        currency = self.currency
        if not currency:
            _logger.warning("Не заполнена валюта!")
            return

        amount = self.amount
        
        amount1 = self.sber_payment_cost
        
        our_reward_amount = self.our_sber_reward
        
        not_our_reward_amount = self.non_our_sber_reward
        
        best_rate = self.best_rate
        if not best_rate:
            _logger.warning("Не заполнена лучшая ставка!")
            return
        
        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Не заполнен Номер заявки!")
            return
        
        if not self.subagent_payer_ids:
            _logger.warning("Не заполнен Плательщик субагента!")
        
        if not self.subagent_payer_ids:
            _logger.warning("Не заполнен Плательщик субагента!")
            return

        agentka_wallet = wallet_model.search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        subagent_payer = self._get_first_payer(subagent)
        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer
        
        # --- Order 1
        if amount:
            order1 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Формируем долг в валюте на Сумма заявки по заявке {record_id} для конвертации",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order1.id,
                **self._get_currency_fields(currency, amount)
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'order_id': [(6, 0, [order1.id])],
                'partner_id': contragent.id,
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 1")

        # --- Order 2
        if amount:
            order2 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount,
                'rate': best_rate,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Проводим конвертацию Суммы заявки по курсу {best_rate} в рубли по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order2.id,
                **self._get_currency_fields(currency, -amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order2.id])],
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })

            amount_in_rub = amount * best_rate
            if amount_in_rub:
                self._create_money({
                    'date': date,
                    'partner_id': client.id,
                    'currency': 'rub',
                    'state': 'positive',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order2.id,
                    **self._get_currency_fields('rub', amount_in_rub),
                })
                self._create_reconciliation({
                    'date': date,
                    'currency': 'rub',
                    **self._get_reconciliation_currency_fields('rub', amount_in_rub),
                    'partner_id': contragent.id,
                    'order_id': [(6, 0, [order2.id])],
                    'sender_id': [(6, 0, [client_payer.id])],
                    'receiver_id': [(6, 0, [agent_payer.id])],
                    'wallet_id': agentka_wallet.id,
                })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 2")

        # --- Order 3
        if our_reward_amount:
            order3 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': our_reward_amount,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order3.id,
                **self._get_currency_fields('rub', our_reward_amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', our_reward_amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order3.id])],
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не заполнена, не создаем ордер 3")

        # --- Order 4
        if not_our_reward_amount:
            order4 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': not_our_reward_amount,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение не наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order4.id,
                **self._get_currency_fields('rub', not_our_reward_amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', not_our_reward_amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order4.id])],
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не наше не заполнена, не создаем ордер 4")

        # --- Order 5
        if amount:
            order5 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': subagent.id,
                'payer_2_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата валюты по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order5.id,
                **self._get_currency_fields(currency, -amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order5.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты валюты не заполнена, не создаем ордер 5")
            
        # --- Order 6
        if amount1:
            order6 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': subagent.id,
                'payer_2_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'amount': amount1,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата вознаграждения субагента за провод платежа по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order6.id,
                **self._get_currency_fields(currency, -amount1),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount1),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order6.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты вознаграждения субагента не заполнена, не создаем ордер 6")

    @api.model
    def _run_fin_entry_automation_client_import(self):
        wallet_model         = self.env['amanat.wallet']         # Кошельки

        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")
        
        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return
        
        # Удаляем старые ордера, сверки и контейнеры
        self._clear_related_documents()

        date = self.supplier_currency_paid_date
        if not date:
            _logger.warning("Не заполнена дата оплаты поставщику!")
            return
        
        _logger.info(f"Установлена дата: {date}")
        
        agent = self.agent_id
        if not agent:
            _logger.warning("Не заполнен агент!")
            return

        if not self.subagent_ids:
            _logger.warning("Не заполнен субагент!")
            return
        
        subagent = self.subagent_ids[0]

        client = self.client_id
        if not client:
            _logger.warning("Не заполнен клиент!")
            return
        
        currency = self.currency
        if not currency:
            _logger.warning("Не заполнена валюта!")
            return

        amount = self.amount
        
        amount1 = self.client_payment_cost
        
        our_reward_amount = self.our_client_reward
        
        not_our_reward_amount = self.non_our_client_reward
        
        best_rate = self.best_rate
        if not best_rate:
            _logger.warning("Не заполнена лучшая ставка!")
            return
        
        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Не заполнен Номер заявки!")
            return
        
        if not self.subagent_payer_ids:
            _logger.warning("Не заполнен Плательщик субагента!")
            return

        agentka_wallet = wallet_model.search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return
        
        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        subagent_payer = self._get_first_payer(subagent)
        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer

        # --- Order 1
        if amount:
            order1 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Формируем долг в валюте на Сумма заявки по заявке {record_id} для конвертации",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order1.id,
                **self._get_currency_fields(currency, amount)
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'order_id': [(6, 0, [order1.id])],
                'partner_id': contragent.id,
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 1")

        # --- Order 2
        if amount:
            order2 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount,
                'rate': best_rate,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Проводим конвертацию Суммы заявки по курсу {best_rate} в рубли по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order2.id,
                **self._get_currency_fields(currency, -amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order2.id])],
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })

            amount_in_rub = amount * best_rate
            if amount_in_rub:
                self._create_money({
                    'date': date,
                    'partner_id': client.id,
                    'currency': 'rub',
                    'state': 'positive',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order2.id,
                    **self._get_currency_fields('rub', amount_in_rub),
                })
                self._create_reconciliation({
                    'date': date,
                    'currency': 'rub',
                    **self._get_reconciliation_currency_fields('rub', amount_in_rub),
                    'partner_id': contragent.id,
                    'order_id': [(6, 0, [order2.id])],
                    'sender_id': [(6, 0, [client_payer.id])],
                    'receiver_id': [(6, 0, [agent_payer.id])],
                    'wallet_id': agentka_wallet.id,
                })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 2")

        # --- Order 3
        if our_reward_amount:
            order3 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': our_reward_amount,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order3.id,
                **self._get_currency_fields('rub', our_reward_amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', our_reward_amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order3.id])],
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не заполнена, не создаем ордер 3")

        # --- Order 4
        if not_our_reward_amount:
            order4 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': client.id,
                'payer_1_id': client_payer.id,
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': not_our_reward_amount,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение не наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order4.id,
                **self._get_currency_fields('rub', not_our_reward_amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', not_our_reward_amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order4.id])],
                'sender_id': [(6, 0, [client_payer.id])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не наше не заполнена, не создаем ордер 4")

        # --- Order 5
        if amount:
            order5 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': subagent.id,
                'payer_2_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата валюты по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order5.id,
                **self._get_currency_fields(currency, -amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order5.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты валюты не заполнена, не создаем ордер 5")
            
        # --- Order 6
        if amount1:
            order6 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': subagent.id,
                'payer_2_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'amount': amount1,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата вознаграждения субагента за провод платежа по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order6.id,
                **self._get_currency_fields(currency, -amount1),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount1),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order6.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты вознаграждения субагента не заполнена, не создаем ордер 6")
    
    @api.model
    def _run_fin_entry_automation_sovok_export(self):
        wallet_model         = self.env['amanat.wallet']        # Кошельки

        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return

        # Удаляем старые ордера, сверки и контейнеры
        self._clear_related_documents()

        date = self.supplier_currency_paid_date
        if not date:
            _logger.warning("Не заполнена дата оплаты поставщику!")
            return
        
        _logger.info(f"Установлена дата: {date}")
        
        agent = self.agent_id
        if not agent:
            _logger.warning("Не заполнен агент!")
            return

        if not self.subagent_ids:
            _logger.warning("Не заполнен субагент!")
            return
        
        subagent = self.subagent_ids[0]

        client = self.client_id
        if not client:
            _logger.warning("Не заполнен клиент!")
            return
        
        currency = self.currency
        if not currency:
            _logger.warning("Не заполнена валюта!")
            return

        amount = self.amount
        
        payment_cost_sovok = self.payment_cost_sovok
        
        our_sovok_reward = self.our_sovok_reward
        
        best_rate = self.best_rate
        if not best_rate:
            _logger.warning("Не заполнена лучшая ставка!")
            return
        
        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Не заполнен Номер заявки!")
            return
        
        if not self.subagent_payer_ids:
            _logger.warning("Не заполнен Плательщик субагента!")
            return
        
        if not self.subagent_payer_ids:
            _logger.warning("Не заполнен Плательщик субагента!")
            return

        agentka_wallet = wallet_model.search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        subagent_payer = self._get_first_payer(subagent)
        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer
        
        # --- Order 1
        if amount:
            order1 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Формируем долг в валюте на Сумма заявки по заявке {record_id} для конвертации",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order1.id,
                **self._get_currency_fields(currency, -amount)
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount),
                'order_id': [(6, 0, [order1.id])],
                'partner_id': contragent.id,
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 1")

        # --- Order 2
        if amount:
            order2 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': amount,
                'rate': best_rate,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Проводим конвертацию Суммы заявки по курсу {best_rate} в рубли по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order2.id,
                **self._get_currency_fields(currency, amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order2.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
            amount_in_rub = amount * best_rate
            if amount_in_rub:
                self._create_money({
                    'date': date,
                    'partner_id': client.id,
                    'currency': 'rub',
                    'state': 'debt',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order2.id,
                    **self._get_currency_fields('rub', -amount_in_rub),
                })
                self._create_reconciliation({
                    'date': date,
                    'currency': 'rub',
                    **self._get_reconciliation_currency_fields('rub', -amount_in_rub),
                    'partner_id': contragent.id,
                    'order_id': [(6, 0, [order2.id])],
                    'sender_id': [(6, 0, [agent_payer.id])],
                    'receiver_id': [(6, 0, [client_payer.id])],
                    'wallet_id': agentka_wallet.id,
                })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 2")

        # --- Order 3
        if our_sovok_reward:
            order3 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': our_sovok_reward,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order3.id,
                **self._get_currency_fields('rub', -our_sovok_reward),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', -our_sovok_reward),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order3.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не заполнена, не создаем ордер 3")
            
        # --- Order 5
        if amount:
            order5 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': subagent.id,
                'payer_1_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата валюты по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order5.id,
                **self._get_currency_fields(currency, amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order5.id])],
                'sender_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты валюты не заполнена, не создаем ордер 5")
            
        # --- Order 6
        if payment_cost_sovok:
            order6 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': subagent.id,
                'payer_1_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': payment_cost_sovok,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата вознаграждения субагента за провод платежа по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order6.id,
                **self._get_currency_fields(currency, payment_cost_sovok),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, payment_cost_sovok),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order6.id])],
                'sender_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты вознаграждения субагента не заполнена, не создаем ордер 6")

    @api.model
    def _run_fin_entry_automation_sber_export(self):
        wallet_model         = self.env['amanat.wallet']         # Кошельки

        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")

        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return

        # Удаляем старые ордера, сверки и контейнеры
        self._clear_related_documents()

        date = self.supplier_currency_paid_date
        if not date:
            _logger.warning("Не заполнена дата оплаты поставщику!")
            return
        
        _logger.info(f"Установлена дата: {date}")
        
        agent = self.agent_id
        if not agent:
            _logger.warning("Не заполнен агент!")
            return

        if not self.subagent_ids:
            _logger.warning("Не заполнен субагент!")
            return
        
        subagent = self.subagent_ids[0]

        client = self.client_id
        if not client:
            _logger.warning("Не заполнен клиент!")
            return
        
        currency = self.currency
        if not currency:
            _logger.warning("Не заполнена валюта!")
            return

        amount = self.amount
        
        amount1 = self.sber_payment_cost
        
        our_reward_amount = self.our_sber_reward
        
        not_our_reward_amount = self.non_our_sber_reward
        
        best_rate = self.best_rate
        if not best_rate:
            _logger.warning("Не заполнена лучшая ставка!")
            return
        
        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Не заполнен Номер заявки!")
            return
        
        if not self.subagent_payer_ids:
            _logger.warning("Не заполнен Плательщик субагента!")
            return
        
        if not self.subagent_payer_ids:
            _logger.warning("Не заполнен Плательщик субагента!")
            return

        agentka_wallet = wallet_model.search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return

        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        subagent_payer = self._get_first_payer(subagent)
        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer
        
        # --- Order 1
        if amount:
            order1 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id':agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Формируем долг в валюте на Сумма заявки по заявке {record_id} для конвертации",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order1.id,
                **self._get_currency_fields(currency, -amount)
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, -amount),
                'order_id': [(6, 0, [order1.id])],
                'partner_id': contragent.id,
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 1")

        # --- Order 2
        if amount:
            order2 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': amount,
                'rate': best_rate,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Проводим конвертацию Суммы заявки по курсу {best_rate} в рубли по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order2.id,
                **self._get_currency_fields(currency, amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order2.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })

            amount_in_rub = amount * best_rate
            if amount_in_rub:
                self._create_money({
                    'date': date,
                    'partner_id': client.id,
                    'currency': 'rub',
                    'state': 'debt',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order2.id,
                    **self._get_currency_fields('rub', -amount_in_rub),
                })
                self._create_reconciliation({
                    'date': date,
                    'currency': 'rub',
                    **self._get_reconciliation_currency_fields('rub', amount_in_rub),
                    'partner_id': contragent.id,
                    'order_id': [(6, 0, [order2.id])],
                    'sender_id': [(6, 0, [agent_payer.id])],
                    'receiver_id': [(6, 0, [client_payer.id])],
                    'wallet_id': agentka_wallet.id,
                })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 2")

        # --- Order 3
        if our_reward_amount:
            order3 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': our_reward_amount,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order3.id,
                **self._get_currency_fields('rub', -our_reward_amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', -our_reward_amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order3.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не заполнена, не создаем ордер 3")

        # --- Order 4
        if not_our_reward_amount:
            order4 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': not_our_reward_amount,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение не наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order4.id,
                **self._get_currency_fields('rub', -not_our_reward_amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', -not_our_reward_amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order4.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не наше не заполнена, не создаем ордер 4")

        # --- Order 5
        if amount:
            order5 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': subagent.id,
                'payer_1_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата валюты по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order5.id,
                **self._get_currency_fields(currency, amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order5.id])],
                'sender_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты валюты не заполнена, не создаем ордер 5")
            
        # --- Order 6
        if amount1:
            order6 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': subagent.id,
                'payer_1_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount1,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата вознаграждения субагента за провод платежа по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order6.id,
                **self._get_currency_fields(currency, amount1),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount1),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order6.id])],
                'sender_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты вознаграждения субагента не заполнена, не создаем ордер 6")

    @api.model
    def _run_fin_entry_automation_client_export(self):
        wallet_model         = self.env['amanat.wallet']         # Кошельки

        record_id = self.id
        _logger.info(f"Получен ID заявки: {record_id}")
        
        contragent = self.contragent_id
        if not contragent:
            _logger.warning("Контрагент не найден")
            return
        
        # Удаляем старые ордера, сверки и контейнеры
        self._clear_related_documents()

        date = self.supplier_currency_paid_date
        if not date:
            _logger.warning("Не заполнена дата оплаты поставщику!")
            return
        
        _logger.info(f"Установлена дата: {date}")
        
        agent = self.agent_id
        if not agent:
            _logger.warning("Не заполнен агент!")
            return

        if not self.subagent_ids:
            _logger.warning("Не заполнен субагент!")
            return
        
        subagent = self.subagent_ids[0]

        client = self.client_id
        if not client:
            _logger.warning("Не заполнен клиент!")
            return
        
        currency = self.currency
        if not currency:
            _logger.warning("Не заполнена валюта!")
            return

        amount = self.amount
        
        amount1 = self.client_payment_cost
        
        our_reward_amount = self.our_client_reward
        
        not_our_reward_amount = self.non_our_client_reward
        
        best_rate = self.best_rate
        if not best_rate:
            _logger.warning("Не заполнена лучшая ставка!")
            return
        
        num_zayavka = self.zayavka_num
        if not num_zayavka:
            _logger.warning("Не заполнен Номер заявки!")
            return
        
        if not self.subagent_payer_ids:
            _logger.warning("Не заполнен Плательщик субагента!")
            return

        agentka_wallet = wallet_model.search([('name', '=', 'Агентка')], limit=1)
        if not agentka_wallet:
            _logger.warning("Кошелек 'Агентка' не найден.")
            return
        
        client_payer = self._get_first_payer(client)
        agent_payer = self._get_first_payer(agent)
        subagent_payer = self._get_first_payer(subagent)
        temp_subagent_payer = self.subagent_payer_ids and self.subagent_payer_ids[0] or subagent_payer

        # --- Order 1
        if amount:
            order1 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Формируем долг в валюте на Сумма заявки по заявке {record_id} для конвертации",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order1.id,
                **self._get_currency_fields(currency, -amount)
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'order_id': [(6, 0, [order1.id])],
                'partner_id': contragent.id,
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 1")

        # --- Order 2
        if amount:
            order2 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': amount,
                'rate': best_rate,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Проводим конвертацию Суммы заявки по курсу {best_rate} в рубли по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order2.id,
                **self._get_currency_fields(currency, amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order2.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })

            amount_in_rub = amount * best_rate
            if amount_in_rub:
                self._create_money({
                    'date': date,
                    'partner_id': client.id,
                    'currency': 'rub',
                    'state': 'debt',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order2.id,
                    **self._get_currency_fields('rub', -amount_in_rub),
                })
                self._create_reconciliation({
                    'date': date,
                    'currency': 'rub',
                    **self._get_reconciliation_currency_fields('rub', -amount_in_rub),
                    'partner_id': contragent.id,
                    'order_id': [(6, 0, [order2.id])],
                    'sender_id': [(6, 0, [agent_payer.id])],
                    'receiver_id': [(6, 0, [client_payer.id])],
                    'wallet_id': agentka_wallet.id,
                })
        else:
            _logger.info("Сумма заявки не заполнена, не создаем ордер 2")

        # --- Order 3
        if our_reward_amount:
            order3 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': our_reward_amount,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order3.id,
                **self._get_currency_fields('rub', -our_reward_amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', -our_reward_amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order3.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не заполнена, не создаем ордер 3")

        # --- Order 4
        if not_our_reward_amount:
            order4 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': agent.id,
                'payer_1_id': agent_payer.id,
                'partner_2_id': client.id,
                'payer_2_id': client_payer.id,
                'amount': not_our_reward_amount,
                'currency': 'rub',
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'comment': f"Вознаграждение не наше по заявке {record_id}",
                'zayavka_ids': [(6, 0, [record_id])]
            })
            self._create_money({
                'date': date,
                'partner_id': client.id,
                'currency': 'rub',
                'state': 'debt',
                'wallet_id': agentka_wallet.id,
                'order_id': order4.id,
                **self._get_currency_fields('rub', -not_our_reward_amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': 'rub',
                **self._get_reconciliation_currency_fields('rub', -not_our_reward_amount),
                'partner_id': contragent.id,
                'order_id': [(6, 0, [order4.id])],
                'sender_id': [(6, 0, [agent_payer.id])],
                'receiver_id': [(6, 0, [client_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма вознаграждения не наше не заполнена, не создаем ордер 4")

        # --- Order 5
        if amount:
            order5 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': subagent.id,
                'payer_1_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата валюты по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order5.id,
                **self._get_currency_fields(currency, amount),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order5.id])],
                'sender_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты валюты не заполнена, не создаем ордер 5")
            
        # --- Order 6
        if amount1:
            order6 = self._create_order({
                'date': date,
                'type': 'transfer',
                'partner_1_id': subagent.id,
                'payer_1_id': temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),
                'partner_2_id': agent.id,
                'payer_2_id': agent_payer.id,
                'amount': amount1,
                'currency': currency,
                'wallet_1_id': agentka_wallet.id,
                'wallet_2_id': agentka_wallet.id,
                'zayavka_ids': [(6, 0, [record_id])],
                'comment': f"Оплата вознаграждения субагента за провод платежа по заявке {record_id}",
            })
            self._create_money({
                'date': date,
                'partner_id': subagent.id,
                'currency': currency,
                'state': 'positive',
                'wallet_id': agentka_wallet.id,
                'order_id': order6.id,
                **self._get_currency_fields(currency, amount1),
            })
            self._create_reconciliation({
                'date': date,
                'currency': currency,
                **self._get_reconciliation_currency_fields(currency, amount1),
                'partner_id': subagent.id,
                'order_id': [(6, 0, [order6.id])],
                'sender_id': [(6, 0, [temp_subagent_payer.id if temp_subagent_payer else (subagent_payer.id if subagent_payer else False),])],
                'receiver_id': [(6, 0, [agent_payer.id])],
                'wallet_id': agentka_wallet.id,
            })
        else:
            _logger.info("Сумма оплаты вознаграждения субагента не заполнена, не создаем ордер 6")