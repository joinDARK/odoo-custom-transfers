import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)

class CreateOrderZayavka(models.Model):
    _inherit = 'amanat.zayavka'

    def action_create_orders_fin(self):
        for zayavka in self:
            # 1. Фильтр: только для Совкомбанк и Импорт
            if not zayavka.contragent_id or zayavka.contragent_id.name != "Совкомбанк":
                continue
            if zayavka.deal_type != "import":
                continue

            # 2. Анти-дубль: удаляем старые ордера, контейнеры и сверки
            orders = zayavka.order_ids
            for order in orders:
                # Удаляем сверки
                self.env['amanat.reconciliation'].search([('order_id', '=', order.id)]).unlink()
                # Удаляем контейнеры
                order.money_ids.unlink()
                # Удаляем ордер
                order.unlink()

            # 3. Получаем данные из заявки
            date = zayavka.supplier_currency_paid_date
            agent = zayavka.agent_id
            subagent = zayavka.subagent_ids and zayavka.subagent_ids[0] or False
            client = zayavka.client_id
            currency = zayavka.currency
            amount1 = zayavka.amount
            amount2 = zayavka.payment_cost_sovok
            our_reward = zayavka.our_sovok_reward
            best_rate = zayavka.best_rate
            request_number = zayavka.zayavka_num

            if not (agent and subagent and client and currency and amount1 is not None and amount2 is not None and our_reward is not None and best_rate is not None):
                _logger.warning("Не заполнены обязательные поля для заявки %s", zayavka.id)
                continue

            # 4. Плательщики
            client_payer = client.payer_ids and client.payer_ids[0] or False
            agent_payer = agent.payer_ids and agent.payer_ids[0] or False
            subagent_payer = subagent and subagent.payer_ids and subagent.payer_ids[0] or False

            if not (client_payer and agent_payer and subagent_payer):
                _logger.warning("Не найден плательщик для одного из участников заявки %s", zayavka.id)
                continue

            # 5. Кошелек "Агентка"
            wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
            if not wallet:
                raise Exception('Кошелек "Агентка" не найден!')

            # 6. Создание ордеров, контейнеров, сверок
            # Order 1: Клиент → Агент, сумма = amount1
            order1 = None
            if amount1:
                order1 = self._create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner_1_id': client.id,
                    'payer_1_id': client_payer.id,
                    'partner_2_id': agent.id,
                    'payer_2_id': agent_payer.id,
                    'amount': amount1,
                    'currency': currency,
                    'wallet_1_id': wallet.id,
                    'wallet_2_id': wallet.id,
                    'comment': f'Формируем долг в валюте на Сумма заявки по заявке {request_number} для конвертации',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
                self._create_money({
                    'date': date,
                    'partner_id': client.id,
                    'currency': currency,
                    'state': 'positive',
                    **self._get_currency_fields(currency, amount1),
                    'wallet_id': wallet.id,
                    'order_id': order1.id,
                })
                vals = self._get_currency_fields(currency, amount1)
                vals.pop('amount', None)
                self._create_reconciliation({
                    'date': date,
                    'currency': currency,
                    **vals,
                    'order_id': [(4, order1.id)],
                    'partner_id': zayavka.contragent_id.id,
                    'sender_id': [(4, client_payer.id)],
                    'receiver_id': [(4, agent_payer.id)],
                    'wallet_id': wallet.id,
                })

            # Order 2: Клиент → Агент, сумма = amount1, с конвертацией по лучшему курсу
            order2 = None
            if amount1:
                order2 = self._create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner_1_id': client.id,
                    'payer_1_id': client_payer.id,
                    'partner_2_id': agent.id,
                    'payer_2_id': agent_payer.id,
                    'amount': amount1,
                    'currency': currency,
                    'wallet_1_id': wallet.id,
                    'wallet_2_id': wallet.id,
                    'rate': best_rate,
                    'comment': f'Проводим конвертацию Суммы заявки по курсу {best_rate} в рубли по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
                # Контейнер долг
                self._create_money({
                    'date': date,
                    'partner_id': client.id,
                    'currency': currency,
                    'state': 'debt',
                    'wallet_id': wallet.id,
                    'order_id': order2.id,
                    **self._get_currency_fields(currency, -amount1),
                })
                # Контейнер положительный (RUB)
                amount_in_rub = amount1 * best_rate
                if amount_in_rub:
                    self._create_money({
                        'date': date,
                        'partner_id': client.id,
                        'currency': 'rub',
                        'state': 'positive',
                        'wallet_id': wallet.id,
                        'order_id': order2.id,
                        **self._get_currency_fields('rub', amount_in_rub),
                    })
                # Сверки для Order 2
                vals = self._get_currency_fields(currency, -amount1)
                vals.pop('amount', None)
                self._create_reconciliation({
                    'date': date,
                    'currency': currency,
                    **vals,
                    'order_id': [(4, order2.id)],
                    'partner_id': zayavka.contragent_id.id,
                    'sender_id': [(4, client_payer.id)],
                    'receiver_id': [(4, agent_payer.id)],
                    'wallet_id': wallet.id,
                })
                if amount_in_rub:
                    vals_rub = self._get_currency_fields('rub', amount_in_rub)
                    vals_rub.pop('amount', None)
                    self._create_reconciliation({
                        'date': date,
                        'currency': 'rub',
                        **vals_rub,
                        'order_id': [(4, order2.id)],
                        'partner_id': zayavka.contragent_id.id,
                        'sender_id': [(4, client_payer.id)],
                        'receiver_id': [(4, agent_payer.id)],
                        'wallet_id': wallet.id,
                    })

            # Order 3: Клиент → Агент, вознаграждение наше, сумма = our_reward, валюта = RUB
            order3 = None
            if our_reward:
                order3 = self._create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner_1_id': client.id,
                    'payer_1_id': client_payer.id,
                    'partner_2_id': agent.id,
                    'payer_2_id': agent_payer.id,
                    'amount': our_reward,
                    'currency': 'rub',
                    'wallet_1_id': wallet.id,
                    'wallet_2_id': wallet.id,
                    'comment': f'Вознаграждение наше по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
                self._create_money({
                    'date': date,
                    'partner_id': client.id,
                    'currency': 'rub',
                    **self._get_currency_fields('rub', our_reward),
                    'state': 'positive',
                    'wallet_id': wallet.id,
                    'order_id': order3.id,
                })
                vals = self._get_currency_fields('rub', our_reward)
                vals.pop('amount', None)
                self._create_reconciliation({
                    'date': date,
                    'currency': 'rub',
                    **vals,
                    'order_id': [(4, order3.id)],
                    'partner_id': zayavka.contragent_id.id,
                    'sender_id': [(4, client_payer.id)],
                    'receiver_id': [(4, agent_payer.id)],
                    'wallet_id': wallet.id,
                })

            # Order 5: Агент → Субагент, сумма = amount1
            order5 = None
            if amount1:
                order5 = self._create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner_1_id': agent.id,
                    'payer_1_id': agent_payer.id,
                    'partner_2_id': subagent.id,
                    'payer_2_id': subagent_payer.id,
                    'amount': amount1,
                    'currency': currency,
                    'wallet_1_id': wallet.id,
                    'wallet_2_id': wallet.id,
                    'comment': f'Оплата валюты по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
                self._create_money({
                    'date': date,
                    'partner_id': subagent.id,
                    'currency': currency,
                    **self._get_currency_fields(currency, -amount1),
                    'state': 'debt',
                    'wallet_id': wallet.id,
                    'order_id': order5.id,
                })
                vals = self._get_currency_fields(currency, -amount1)
                vals.pop('amount', None)
                self._create_reconciliation({
                    'date': date,
                    'currency': currency,
                    **vals,
                    'order_id': [(4, order5.id)],
                    'partner_id': subagent.id,
                    'sender_id': [(4, agent_payer.id)],
                    'receiver_id': [(4, subagent_payer.id)],
                    'wallet_id': wallet.id,
                })

            # Order 6: Агент → Субагент, сумма = amount2
            order6 = None
            if amount2:
                order6 = self._create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner_1_id': agent.id,
                    'payer_1_id': agent_payer.id,
                    'partner_2_id': subagent.id,
                    'payer_2_id': subagent_payer.id,
                    'amount': amount2,
                    'currency': currency,
                    'wallet_1_id': wallet.id,
                    'wallet_2_id': wallet.id,
                    'comment': f'Оплата вознаграждения субагента за провод платежа по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
                self._create_money({
                    'date': date,
                    'partner_id': subagent.id,
                    'currency': currency,
                    **self._get_currency_fields(currency, -amount2),
                    'state': 'debt',
                    'wallet_id': wallet.id,
                    'order_id': order6.id,
                })
                vals = self._get_currency_fields(currency, -amount2)
                vals.pop('amount', None)
                self._create_reconciliation({
                    'date': date,
                    'currency': currency,
                    **vals,
                    'order_id': [(4, order6.id)],
                    'partner_id': subagent.id,
                    'sender_id': [(4, agent_payer.id)],
                    'receiver_id': [(4, subagent_payer.id)],
                    'wallet_id': wallet.id,
                })

        # --- (Скрипт для Совкомбанк Экспорт) ---
        for zayavka in self:
            # Фильтр: только для Совкомбанк и Экспорт
            if not zayavka.contragent_id or zayavka.contragent_id.name != "Совкомбанк":
                continue
            if zayavka.deal_type != "export":
                continue

            # Анти-дубль: удаляем старые ордера, контейнеры и сверки для данной заявки
            old_orders = self.env['amanat.order'].search([('zayavka_ids', 'in', zayavka.id)])
            if old_orders:
                # Удаляем сверки
                old_recs = self.env['amanat.reconciliation'].search([('order_id', 'in', old_orders.ids)])
                old_recs.unlink()
                # Удаляем контейнеры
                old_money = self.env['amanat.money'].search([('order_id', 'in', old_orders.ids)])
                old_money.unlink()
                # Удаляем ордера
                old_orders.unlink()

            # Извлекаем нужные поля из заявки
            date = zayavka.supplier_currency_paid_date
            agent = zayavka.agent_id
            subagent = zayavka.subagent_ids and zayavka.subagent_ids[0] or False
            client = zayavka.client_id
            currency = zayavka.currency
            amount1 = zayavka.amount
            amount2 = zayavka.sovok_payment_cost
            our_reward = zayavka.our_sovok_reward
            best_rate = zayavka.best_rate
            request_number = zayavka.zayavka_num
            if not (agent and subagent and client and currency and request_number and best_rate is not None):
                continue
            if any(x is None for x in [amount1, amount2, our_reward]):
                continue

            # Получаем плательщиков
            client_payer = client.payer_ids and client.payer_ids[0] or False
            agent_payer = agent.payer_ids and agent.payer_ids[0] or False
            subagent_payer = subagent and subagent.payer_ids and subagent.payer_ids[0] or False
            if not (client_payer and agent_payer and subagent):
                continue

            # Кошелек "Агентка"
            agentka_wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
            if not agentka_wallet:
                continue

            # --- Создание ордеров ---
            order_ids = []
            def create_order(vals):
                order = self._create_order(vals)
                order_ids.append(order.id)
                return order

            order1 = order2 = order3 = order5 = order6 = None
            if amount1 != 0:
                order1 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': agent.id,
                    'payer1_id': agent_payer.id,
                    'partner2_id': client.id,
                    'payer2_id': client_payer.id,
                    'amount': amount1,
                    'currency': currency,
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Формируем долг в валюте по заявке {request_number} для конвертации',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
            if amount1 != 0:
                order2 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': agent.id,
                    'payer1_id': agent_payer.id,
                    'partner2_id': client.id,
                    'payer2_id': client_payer.id,
                    'amount': amount1,
                    'rate': best_rate,
                    'currency': currency,
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Проводим конвертацию Суммы заявки по курсу {best_rate} в рубли по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
            if our_reward != 0:
                order3 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': agent.id,
                    'payer1_id': agent_payer.id,
                    'partner2_id': client.id,
                    'payer2_id': client_payer.id,
                    'amount': our_reward,
                    'currency': 'rub',
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Вознаграждение наше по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
            if amount1 != 0:
                order5 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': subagent.id,
                    'payer1_id': subagent_payer.id,
                    'partner2_id': agent.id,
                    'payer2_id': agent_payer.id,
                    'amount': amount1,
                    'currency': currency,
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Оплата валюты по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
            if amount2 != 0:
                order6 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': subagent.id,
                    'payer1_id': subagent_payer.id,
                    'partner2_id': agent.id,
                    'payer2_id': agent_payer.id,
                    'amount': amount2,
                    'currency': currency,
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Оплата вознаграждения субагента за провод платежа по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })

            # --- Создание контейнеров ---
            def get_currency_fields(currency, amount):
                fields = {}
                if currency == 'rub':
                    fields['sum_rub'] = amount
                elif currency == 'rub_cashe':
                    fields['sum_rub_cashe'] = amount
                elif currency == 'usd':
                    fields['sum_usd'] = amount
                elif currency == 'usd_cashe':
                    fields['sum_usd_cashe'] = amount
                elif currency == 'usdt':
                    fields['sum_usdt'] = amount
                elif currency == 'cny':
                    fields['sum_cny'] = amount
                elif currency == 'cny_cashe':
                    fields['sum_cny_cashe'] = amount
                elif currency == 'euro':
                    fields['sum_euro'] = amount
                elif currency == 'euro_cashe':
                    fields['sum_euro_cashe'] = amount
                elif currency == 'aed':
                    fields['sum_aed'] = amount
                elif currency == 'aed_cashe':
                    fields['sum_aed_cashe'] = amount
                elif currency == 'thb':
                    fields['sum_thb'] = amount
                elif currency == 'thb_cashe':
                    fields['sum_thb_cashe'] = amount
                return fields

            Money = self.env['amanat.money']
            if amount1 != 0 and order1:
                self._create_money({
                    'date': date,
                    'holder_id': client.id,
                    'currency': currency,
                    'state': 'debt',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order1.id,
                    **self._get_currency_fields(currency, -amount1),
                })
            if amount1 != 0 and order2:
                self._create_money({
                    'date': date,
                    'holder_id': client.id,
                    'currency': currency,
                    'state': 'positive',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order2.id,
                    **self._get_currency_fields(currency, amount1),
                })
                amount_in_rub = amount1 * best_rate
                if amount_in_rub != 0:
                    self._create_money({
                        'date': date,
                        'holder_id': client.id,
                        'currency': 'rub',
                        'state': 'debt',
                        'wallet_id': agentka_wallet.id,
                        'order_id': order2.id,
                        **self._get_currency_fields('rub', -amount_in_rub),
                    })
            if our_reward != 0 and order3:
                self._create_money({
                    'date': date,
                    'holder_id': client.id,
                    'currency': 'rub',
                    'state': 'debt',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order3.id,
                    **self._get_currency_fields('rub', -our_reward),
                })
            if amount1 != 0 and order5:
                self._create_money({
                    'date': date,
                    'holder_id': subagent.id,
                    'currency': currency,
                    'state': 'positive',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order5.id,
                    **self._get_currency_fields(currency, amount1),
                })
            if amount2 != 0 and order6:
                self._create_money({
                    'date': date,
                    'holder_id': subagent.id,
                    'currency': currency,
                    'state': 'positive',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order6.id,
                    **self._get_currency_fields(currency, amount2),
                })

            # --- Создание сверок ---
            def create_reconciliation(order, date, currency, amount, sender, receiver, wallet, partner, force_negative=False):
                amt = -abs(amount) if force_negative and amount > 0 else amount
                if amt == 0:
                    return
                vals = self._get_currency_fields(currency, amt)
                vals.pop('amount', None)
                self._create_reconciliation({
                    'date': date,
                    'currency': currency,
                    **vals,
                    'order_id': [(4, order.id)],
                    'partner_id': partner.id if partner else False,
                    'sender_id': sender.id if sender else False,
                    'receiver_id': receiver.id if receiver else False,
                    'wallet_id': wallet.id if wallet else False,
                })

            if amount1 != 0 and order1:
                create_reconciliation(order1, date, currency, amount1, agent_payer, client_payer, agentka_wallet, zayavka.contragent_id, force_negative=True)
            if amount1 != 0 and order2:
                create_reconciliation(order2, date, currency, amount1, agent_payer, client_payer, agentka_wallet, zayavka.contragent_id)
                amount_in_rub = amount1 * best_rate
                if amount_in_rub != 0:
                    create_reconciliation(order2, date, 'rub', amount_in_rub, agent_payer, client_payer, agentka_wallet, zayavka.contragent_id, force_negative=True)
            if our_reward != 0 and order3:
                create_reconciliation(order3, date, 'rub', our_reward, agent_payer, client_payer, agentka_wallet, zayavka.contragent_id, force_negative=True)
            if amount1 != 0 and order5:
                create_reconciliation(order5, date, currency, amount1, subagent_payer, agent_payer, agentka_wallet, subagent)
            if amount2 != 0 and order6:
                create_reconciliation(order6, date, currency, amount2, subagent_payer, agent_payer, agentka_wallet, subagent)

        # --- (Скрипт для Сбербанк Экспорт) ---
        for zayavka in self:
            # Фильтр: только для Сбербанк и Экспорт
            if not zayavka.contragent_id or zayavka.contragent_id.name != "Сбербанк":
                continue
            if zayavka.deal_type != "export":
                continue

            # Анти-дубль: удаляем старые ордера, контейнеры и сверки для данной заявки
            old_orders = self.env['amanat.order'].search([('zayavka_ids', 'in', zayavka.id)])
            if old_orders:
                # Удаляем сверки
                old_recs = self.env['amanat.reconciliation'].search([('order_id', 'in', old_orders.ids)])
                old_recs.unlink()
                # Удаляем контейнеры
                old_money = self.env['amanat.money'].search([('order_id', 'in', old_orders.ids)])
                old_money.unlink()
                # Удаляем ордера
                old_orders.unlink()

            # Извлекаем нужные поля из заявки
            date = zayavka.supplier_currency_paid_date
            agent = zayavka.agent_id
            subagent = zayavka.subagent_ids and zayavka.subagent_ids[0] or False
            client = zayavka.client_id
            currency = zayavka.currency
            amount1 = zayavka.amount
            amount2 = zayavka.sber_payment_cost
            our_reward = zayavka.our_sber_reward
            not_our_reward = zayavka.non_our_sber_reward
            best_rate = zayavka.best_rate
            request_number = zayavka.zayavka_num
            if not (agent and subagent and client and currency and request_number and best_rate is not None):
                continue
            if any(x is None for x in [amount1, amount2, our_reward, not_our_reward]):
                continue

            # Получаем плательщиков
            client_payer = client.payer_ids and client.payer_ids[0] or False
            agent_payer = agent.payer_ids and agent.payer_ids[0] or False
            subagent_payer = subagent and subagent.payer_ids and subagent.payer_ids[0] or False
            if not (client_payer and agent_payer and subagent):
                continue

            # Кошелек "Агентка"
            agentka_wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
            if not agentka_wallet:
                continue

            # --- Создание ордеров ---
            order_ids = []
            def create_order(vals):
                order = self.env['amanat.order'].create(vals)
                order_ids.append(order.id)
                return order

            order1 = order2 = order3 = order4 = order5 = order6 = None
            if amount1 != 0:
                order1 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': agent.id,
                    'payer1_id': agent_payer.id,
                    'partner2_id': client.id,
                    'payer2_id': client_payer.id,
                    'amount': amount1,
                    'currency': currency,
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Формируем долг в валюте по заявке {request_number} для конвертации',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
            if amount1 != 0:
                order2 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': agent.id,
                    'payer1_id': agent_payer.id,
                    'partner2_id': client.id,
                    'payer2_id': client_payer.id,
                    'amount': amount1,
                    'rate': best_rate,
                    'currency': currency,
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Проводим конвертацию Суммы заявки по курсу {best_rate} в рубли по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
            if our_reward != 0:
                order3 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': agent.id,
                    'payer1_id': agent_payer.id,
                    'partner2_id': client.id,
                    'payer2_id': client_payer.id,
                    'amount': our_reward,
                    'currency': 'rub',
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Вознаграждение наше по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
            if not_our_reward != 0:
                order4 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': agent.id,
                    'payer1_id': agent_payer.id,
                    'partner2_id': client.id,
                    'payer2_id': client_payer.id,
                    'amount': not_our_reward,
                    'currency': 'rub',
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Вознаграждение не наше по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
            if amount1 != 0:
                order5 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': subagent.id,
                    'payer1_id': subagent_payer.id,
                    'partner2_id': agent.id,
                    'payer2_id': agent_payer.id,
                    'amount': amount1,
                    'currency': currency,
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Оплата валюты по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })
            if amount2 != 0:
                order6 = create_order({
                    'date': date,
                    'type': 'transfer',
                    'partner1_id': subagent.id,
                    'payer1_id': subagent_payer.id,
                    'partner2_id': agent.id,
                    'payer2_id': agent_payer.id,
                    'amount': amount2,
                    'currency': currency,
                    'wallet1_id': agentka_wallet.id,
                    'wallet2_id': agentka_wallet.id,
                    'comment': f'Оплата вознаграждения субагента за провод платежа по заявке {request_number}',
                    'zayavka_ids': [(6, 0, [zayavka.id])],
                })

            # --- Создание контейнеров ---
            def get_currency_fields(currency, amount):
                fields = {}
                if currency == 'rub':
                    fields['sum_rub'] = amount
                elif currency == 'rub_cashe':
                    fields['sum_rub_cashe'] = amount
                elif currency == 'usd':
                    fields['sum_usd'] = amount
                elif currency == 'usd_cashe':
                    fields['sum_usd_cashe'] = amount
                elif currency == 'usdt':
                    fields['sum_usdt'] = amount
                elif currency == 'cny':
                    fields['sum_cny'] = amount
                elif currency == 'cny_cashe':
                    fields['sum_cny_cashe'] = amount
                elif currency == 'euro':
                    fields['sum_euro'] = amount
                elif currency == 'euro_cashe':
                    fields['sum_euro_cashe'] = amount
                elif currency == 'aed':
                    fields['sum_aed'] = amount
                elif currency == 'aed_cashe':
                    fields['sum_aed_cashe'] = amount
                elif currency == 'thb':
                    fields['sum_thb'] = amount
                elif currency == 'thb_cashe':
                    fields['sum_thb_cashe'] = amount
                return fields

            Money = self.env['amanat.money']
            if amount1 != 0 and order1:
                Money.create({
                    'date': date,
                    'holder_id': client.id,
                    'currency': currency,
                    'state': 'debt',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order1.id,
                    **self._get_currency_fields(currency, -amount1),
                })
            if amount1 != 0 and order2:
                Money.create({
                    'date': date,
                    'holder_id': client.id,
                    'currency': currency,
                    'state': 'positive',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order2.id,
                    **self._get_currency_fields(currency, amount1),
                })
                amount_in_rub = amount1 * best_rate
                if amount_in_rub != 0:
                    Money.create({
                        'date': date,
                        'holder_id': client.id,
                        'currency': 'rub',
                        'state': 'debt',
                        'wallet_id': agentka_wallet.id,
                        'order_id': order2.id,
                        **self._get_currency_fields('rub', -amount_in_rub),
                    })
            if our_reward != 0 and order3:
                Money.create({
                    'date': date,
                    'holder_id': client.id,
                    'currency': 'rub',
                    'state': 'debt',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order3.id,
                    **self._get_currency_fields('rub', -our_reward),
                })
            if not_our_reward != 0 and order4:
                Money.create({
                    'date': date,
                    'holder_id': client.id,
                    'currency': 'rub',
                    'state': 'debt',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order4.id,
                    **self._get_currency_fields('rub', -not_our_reward),
                })
            if amount1 != 0 and order5:
                Money.create({
                    'date': date,
                    'holder_id': subagent.id,
                    'currency': currency,
                    'state': 'positive',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order5.id,
                    **self._get_currency_fields(currency, amount1),
                })
            if amount2 != 0 and order6:
                Money.create({
                    'date': date,
                    'holder_id': subagent.id,
                    'currency': currency,
                    'state': 'positive',
                    'wallet_id': agentka_wallet.id,
                    'order_id': order6.id,
                    **self._get_currency_fields(currency, amount2),
                })

            # --- Создание сверок ---
            def create_reconciliation(order, date, currency, amount, sender, receiver, wallet, partner, force_negative=False):
                amt = -abs(amount) if force_negative and amount > 0 else amount
                if amt == 0:
                    return
                vals = self._get_currency_fields(currency, amt)
                vals.pop('amount', None)
                self.env['amanat.reconciliation'].create({
                    'date': date,
                    'currency': currency,
                    **vals,
                    'order_id': [(4, order.id)],
                    'partner_id': partner.id if partner else False,
                    'sender_id': sender.id if sender else False,
                    'receiver_id': receiver.id if receiver else False,
                    'wallet_id': wallet.id if wallet else False,
                })

            if amount1 != 0 and order1:
                create_reconciliation(order1, date, currency, amount1, agent_payer, client_payer, agentka_wallet, zayavka.contragent_id, force_negative=True)
            if amount1 != 0 and order2:
                create_reconciliation(order2, date, currency, amount1, agent_payer, client_payer, agentka_wallet, zayavka.contragent_id)
                amount_in_rub = amount1 * best_rate
                if amount_in_rub != 0:
                    create_reconciliation(order2, date, 'rub', amount_in_rub, agent_payer, client_payer, agentka_wallet, zayavka.contragent_id, force_negative=True)
            if our_reward != 0 and order3:
                create_reconciliation(order3, date, 'rub', our_reward, agent_payer, client_payer, agentka_wallet, zayavka.contragent_id, force_negative=True)
            if not_our_reward != 0 and order4:
                create_reconciliation(order4, date, 'rub', not_our_reward, agent_payer, client_payer, agentka_wallet, zayavka.contragent_id, force_negative=True)
            if amount1 != 0 and order5:
                create_reconciliation(order5, date, currency, amount1, subagent_payer, agent_payer, agentka_wallet, subagent)
            if amount2 != 0 and order6:
                create_reconciliation(order6, date, currency, amount2, subagent_payer, agent_payer, agentka_wallet, subagent)

        return True

    def write(self, vals):
        res = super().write(vals)
        # Если изменилось поле оплаты валюты поставщику/субагенту — запускаем автоматизацию
        if 'supplier_currency_paid_date' in vals:
            self.action_create_orders_fin()
        return res