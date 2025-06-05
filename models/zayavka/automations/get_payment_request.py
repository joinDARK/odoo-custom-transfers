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
        # Пример: отправить сообщение в чат заявки
        _logger.info(f'Поле "Выписка разнос" изменилось: было {old_ids}, стало {new_ids}')

        # Определяем сумму заявки по контрагенту
        contragent = self.contragent_id
        if contragent and contragent.name == "Совкомбанк":
            required_sum = self.total_sovok
        elif contragent and contragent.name == "Сбербанк":
            required_sum = self.total_sber
        else:
            required_sum = self.total_client

        extracts = self.extract_delivery_ids
        if not extracts:
            _logger.info("Нет связанных выписок.")
            return

        allocated_sum = 0
        for extract in extracts[:-1]:  # все, кроме последней
            amount = extract.amount or 0  # замените на правильное поле
            allocated_sum += amount

        remaining_sum = required_sum - allocated_sum
        if remaining_sum <= 0:
            _logger.info(f"Заявка {self.zayavka_num} уже полностью погашена.")
            return

        latest_extract = extracts[-1]
        vypiska_date = latest_extract.date
        vypiska_payer = latest_extract.payer
        vypiska_receiver = latest_extract.recipient
        vypiska_amount = latest_extract.amount or 0
        amount_to_process = min(vypiska_amount, remaining_sum)

        wallet = self.env['amanat.wallet'].search([('name', '=', 'Агентка')], limit=1)
        if not wallet:
            _logger.error("Кошелёк 'Агентка' не найден.")
            return

        contragent_for_payer = vypiska_payer.contragents_ids[0] if vypiska_payer and vypiska_payer.contragents_ids else None
        contragent_for_receiver = vypiska_receiver.contragents_ids[0] if vypiska_receiver and vypiska_receiver.contragents_ids else None

        order_vals = {
            'date': vypiska_date,
            'type': 'transfer',  # или нужное значение
            'partner_1_id': contragent_for_payer.id if contragent_for_payer else False,
            'partner_2_id': contragent_for_receiver.id if contragent_for_receiver else False,
            'payer_1_id': vypiska_payer.id if vypiska_payer else False,
            'payer_2_id': vypiska_receiver.id if vypiska_receiver else False,
            'wallet_1_id': wallet.id,
            'wallet_2_id': wallet.id,
            'currency': 'rub',  # или нужное поле
            'amount': amount_to_process,
            'comment': f'оплата рублей по заявке № {self.zayavka_num}',
            'zayavka_ids': [(4, self.id)],
        }
        order = self._create_order(order_vals)

        # Для отправителя (отрицательная сумма)
        money_vals_1 = {
            'date': vypiska_date,
            'partner_id': contragent_for_payer.id if contragent_for_payer else False,
            'currency': 'rub',
            'state': 'debt',  # или нужное значение
            'wallet_id': wallet.id,
            'order_id': order.id,
            **self._get_currency_fields('rub', -amount_to_process)
        }
        self._create_money(money_vals_1)

        # # Для получателя (положительная сумма)
        money_vals_2 = {
            'date': vypiska_date,
            'partner_id': contragent_for_payer.id if contragent_for_payer else False,
            'currency': 'rub',
            'state': 'positive',  # или нужное значение
            'wallet_id': wallet.id,
            'order_id': order.id,
            **self._get_currency_fields('rub', amount_to_process)
        }
        self._create_money(money_vals_2)

        # Для отправителя (отрицательная сумма)
        reconciliation_vals_1 = {
            'date': vypiska_date,
            'partner_id': contragent_for_payer.id if contragent_for_payer else False,
            'currency': 'rub',
            'sum': -amount_to_process,
            'wallet_id': wallet.id,
            'sender_id': [(4, vypiska_payer.id)] if vypiska_payer else [],
            'receiver_id': [(4, vypiska_receiver.id)] if vypiska_receiver else [],
            'order_id': [(4, order.id)],
        }
        self._create_reconciliation(reconciliation_vals_1)

        # Для получателя (положительная сумма)
        reconciliation_vals_2 = {
            'date': vypiska_date,
            'partner_id': contragent_for_receiver.id if contragent_for_receiver else False,
            'currency': 'rub',
            'sum': amount_to_process,
            'wallet_id': wallet.id,
            'sender_id': [(4, vypiska_payer.id)] if vypiska_payer else [],
            'receiver_id': [(4, vypiska_receiver.id)] if vypiska_receiver else [],
            'order_id': [(4, order.id)],
        }
        self._create_reconciliation(reconciliation_vals_2)