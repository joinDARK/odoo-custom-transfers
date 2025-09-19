import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class ZayavkaGetPaymentRequest(models.Model):
    _inherit = 'amanat.zayavka'

    def _on_extract_delivery_ids_changed(self, old_ids, new_ids):
        """
        Этот метод вызывается, когда поле extract_delivery_ids изменилось.
        old_ids, new_ids — это множества id связанных записей до и после изменения.
        Здесь можно прописать любой скрипт/логику.
        """
        _logger.info('=== АВТОМАТИЗАЦИЯ get_payment_request ЗАПУЩЕНА ===')
        _logger.info(f'Заявка ID: {self.id}')
        _logger.info(f'Поле "Выписка разнос" изменилось: было {old_ids}, стало {new_ids}')

        # Определяем добавленные и удаленные выписки
        added_extract_ids = new_ids - old_ids
        removed_extract_ids = old_ids - new_ids
        
        _logger.info(f'Добавленные выписки: {added_extract_ids}')
        _logger.info(f'Удаленные выписки: {removed_extract_ids}')

        # Если нет новых выписок - выходим
        if not added_extract_ids:
            _logger.info("Нет новых выписок для обработки.")
            return

        # Определяем сумму заявки по флагу контрагента
        if self.is_sovcombank_contragent and not self.is_sberbank_contragent:
            _logger.info("Считаем как Совкомбанк")
            required_sum = self.total_sovok
        elif self.is_sberbank_contragent and not self.is_sovcombank_contragent:
            _logger.info("Считаем как Сбербанк")
            required_sum = self.total_sber
        else:
            _logger.info("Считаем как Клиент")
            required_sum = self.total_client

        _logger.info(f"Требуемая сумма для погашения: {required_sum}")

        # Получаем кошелек
        wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet:
            _logger.error("Кошелёк 'Агентка' не найден.")
            return

        # Считаем уже обработанную сумму (из старых выписок)
        old_extracts = self.env['amanat.extract_delivery'].browse(list(old_ids))
        allocated_sum = sum(extract.amount or 0 for extract in old_extracts)
        _logger.info(f"Уже обработанная сумма: {allocated_sum}")

        # Обрабатываем каждую новую выписку
        new_extracts = self.env['amanat.extract_delivery'].browse(list(added_extract_ids))
        for extract in new_extracts:
            remaining_sum = required_sum - allocated_sum
            if remaining_sum <= 0:
                _logger.info(f"Заявка {self.zayavka_num} уже полностью погашена. Пропускаем выписку {extract.id}")
                continue

            vypiska_date = extract.date
            vypiska_payer = extract.payer
            vypiska_receiver = extract.recipient
            vypiska_amount = extract.amount or 0
            amount_to_process = min(vypiska_amount, remaining_sum)

            _logger.info(f"Обрабатываем выписку {extract.id}: сумма={vypiska_amount}, к обработке={amount_to_process}")

            contragent_for_payer = vypiska_payer.contragents_ids[0] if vypiska_payer and vypiska_payer.contragents_ids else None
            contragent_for_receiver = vypiska_receiver.contragents_ids[0] if vypiska_receiver and vypiska_receiver.contragents_ids else None

            # Создаем ордер для этой выписки
            order_vals = {
                'date': vypiska_date,
                'type': 'transfer',
                'partner_1_id': contragent_for_payer.id if contragent_for_payer else False,
                'partner_2_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'payer_1_id': vypiska_payer.id if vypiska_payer else False,
                'payer_2_id': vypiska_receiver.id if vypiska_receiver else False,
                'wallet_1_id': wallet.id,
                'wallet_2_id': wallet.id,
                'currency': 'rub',
                'amount': amount_to_process,
                'comment': f'(ID: {self.id}) оплата рублей по заявке № {self.zayavka_num} (выписка {extract.id})',
                'zayavka_ids': [(4, self.id)],
            }
            order = self._create_order(order_vals)

            # Создаем контейнеры (money) для отправителя (отрицательная сумма)
            money_vals_1 = {
                'date': vypiska_date,
                'partner_id': contragent_for_payer.id if contragent_for_payer else False,
                'currency': 'rub',
                'state': 'debt',
                'wallet_id': wallet.id,
                'order_id': order.id,
                **self._get_currency_fields('rub', -amount_to_process)
            }
            self._create_money(money_vals_1)

            # Создаем контейнеры (money) для получателя (положительная сумма)
            money_vals_2 = {
                'date': vypiska_date,
                'partner_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'currency': 'rub',
                'state': 'positive',
                'wallet_id': wallet.id,
                'order_id': order.id,
                **self._get_currency_fields('rub', amount_to_process)
            }
            self._create_money(money_vals_2)

            # Создаем сверку для отправителя (отрицательная сумма)
            reconciliation_vals_1 = {
                'date': vypiska_date,
                'partner_id': contragent_for_payer.id if contragent_for_payer else False,
                'currency': 'rub',
                'sum': -amount_to_process,
                'wallet_id': wallet.id,
                'order_id': [(4, order.id)],  # Many2many поле
                **self._get_reconciliation_currency_fields('rub', -amount_to_process)
            }
            # Добавляем sender_id и receiver_id если они есть
            if vypiska_payer:
                reconciliation_vals_1['sender_id'] = [(4, vypiska_payer.id)]
            if vypiska_receiver:
                reconciliation_vals_1['receiver_id'] = [(4, vypiska_receiver.id)]
            
            self._create_reconciliation(reconciliation_vals_1)

            # Создаем сверку для получателя (положительная сумма)
            reconciliation_vals_2 = {
                'date': vypiska_date,
                'partner_id': contragent_for_receiver.id if contragent_for_receiver else False,
                'currency': 'rub',
                'sum': amount_to_process,
                'wallet_id': wallet.id,
                'order_id': [(4, order.id)],  # Many2many поле
                **self._get_reconciliation_currency_fields('rub', amount_to_process)
            }
            # Добавляем sender_id и receiver_id если они есть
            if vypiska_payer:
                reconciliation_vals_2['sender_id'] = [(4, vypiska_payer.id)]
            if vypiska_receiver:
                reconciliation_vals_2['receiver_id'] = [(4, vypiska_receiver.id)]
                
            self._create_reconciliation(reconciliation_vals_2)

            # Обновляем обработанную сумму
            allocated_sum += amount_to_process
            _logger.info(f"Выписка {extract.id} обработана. Общая обработанная сумма: {allocated_sum}")

        _logger.info(f'=== АВТОМАТИЗАЦИЯ get_payment_request ЗАВЕРШЕНА ===')