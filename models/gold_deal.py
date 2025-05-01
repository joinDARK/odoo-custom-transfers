from odoo import models, fields, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class GoldDeal(models.Model):
    _name = 'amanat.gold_deal'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Золото сделка'

    # 1. ID – формируется с помощью последовательности с префиксом "Сделка №"
    name = fields.Char(
        string='ID',
        readonly=True,
        default=lambda self: "Сделка №" + str(self.env['ir.sequence'].next_by_code('amanat.gold_deal.sequence')),
        tracking=True
    )

    # 2. Статус – выбор из трёх вариантов
    status = fields.Selection(
        [('open', 'Открыта'), ('closed', 'Закрыта'), ('archived', 'Архив')],
        string='Статус',
        default='open',
        tracking=True
    )

    # 3. Комментарий – однострочное текстовое поле
    comment = fields.Char(string='Комментарий', tracking=True)

    # 4. Дата
    date = fields.Date(string='Дата', tracking=True, default=fields.Date.today)

    # 5. Партнеры – связь один-ко-многим с моделью «Партнеры золото»
    partner_ids = fields.Many2many(
        'amanat.partner_gold',
        relation='amanat_partner_gold_deal_rel',
        column1='gold_deal_id',
        column2='partner_gold_id',
        string='Партнеры',
        tracking=True
    )

    # 6. Чистый вес, гр (Rollup: сумма поля pure_weight из партнеров)
    pure_weight_sum = fields.Float(
        string='Чистый вес, гр (Rollup)',
        compute='_compute_pure_weight_sum',
        store=True,
        tracking=True
    )

    # 7. Общая сумма покупки (Rollup: сумма поля amount_rub из партнеров)
    purchase_total_rub = fields.Float(
        string='Общая сумма покупки',
        compute='_compute_purchase_total_rub',
        store=True,
        tracking=True
    )

    # 8. Сумма закупа в долларах (Rollup: сумма поля purchase_amount_dollar из партнеров)
    purchase_total_dollar = fields.Float(
        string='Сумма закупа в долларах',
        compute='_compute_purchase_total_dollar',
        store=True,
        tracking=True
    )

    # 9. Расходы (Rollup: сумма поля total_expenses из партнеров)
    expenses = fields.Float(
        string='Расходы',
        compute='_compute_expenses',
        store=True,
        tracking=True
    )

    # 10. Услуга (Rollup: сумма поля service из партнеров)
    service = fields.Float(
        string='Услуга',
        compute='_compute_service',
        store=True,
        tracking=True
    )

    # 11. Банк сумм (Rollup: сумма поля bank_sum из партнеров)
    bank_sum = fields.Float(
        string='Банк сумм',
        compute='_compute_bank_sum',
        store=True,
        tracking=True
    )

    # 12. Банк КБ (Rollup: сумма поля bank_kb из партнеров)
    bank_kb = fields.Float(
        string='Банк КБ',
        compute='_compute_bank_kb',
        store=True,
        tracking=True
    )

    # 13. Курьер (Rollup: сумма поля courier из партнеров)
    courier = fields.Float(
        string='Курьер',
        compute='_compute_courier',
        store=True,
        tracking=True
    )

    # 14. Общая сумма (Rollup: сумма поля purchase_usdt из партнеров)
    total_amount = fields.Float(
        string='Общая сумма',
        compute='_compute_total_amount',
        store=True,
        tracking=True
    )

    # 15. Сумма продажи AED (Rollup: сумма поля sale_amount_aed из партнеров)
    sale_amount_aed = fields.Float(
        string='Сумма продажи AED',
        compute='_compute_sale_amount_aed',
        store=True,
        tracking=True
    )

    # 16. Сумма продажи USDT (Rollup: сумма поля purchase_usdt из партнеров)
    sale_amount_usdt = fields.Float(
        string='Сумма продажи USDT',
        compute='_compute_sale_amount_usdt',
        store=True,
        tracking=True
    )

    # 17. Дополнительные расходы
    extra_expenses = fields.Float(string='Дополнительные расходы', tracking=True)

    # 18. Курс итог – вычисляется как Общая сумма покупки / Общая сумм
    final_rate = fields.Float(
        string='Курс итог',
        compute='_compute_final_rate',
        store=True,
        tracking=True
    )

    # 19. Провести вход
    conduct_in = fields.Boolean(string='Провести вход', default=False, tracking=True)

    # 20. Провести выход
    conduct_out = fields.Boolean(string='Провести выход', default=False, tracking=True)

    # 21. Проводка Вита
    vita_posting = fields.Boolean(string='Проводка Вита', default=False, tracking=True)

    # 22. Сверка
    reconciliation = fields.Boolean(string='Сверка', default=False, tracking=True)

    # 23. Перепроводка
    reposting = fields.Boolean(string='Перепроводка', default=False, tracking=True)

    # 24. Пометить на удаление
    mark_for_deletion = fields.Boolean(string='Пометить на удаление', default=False, tracking=True)

    # 25. Сумма по инвойсу
    invoice_amount = fields.Float(string='Сумма по инвойсу', tracking=True)

    # 26. Разница = Общая сумма покупки - Сумма по инвойсу
    difference = fields.Float(
        string='Разница',
        compute='_compute_difference',
        store=True,
        tracking=True
    )

    # 27. Банк – выбор из: Вита, СКБ, Альфа
    bank = fields.Selection(
        [('vita', 'Вита'), ('skb', 'СКБ'), ('alfa', 'Альфа')],
        string='Банк',
        tracking=True
    )

    # 28. Платежка – связь с выпиской разнос (многие ко многим)
    extract_delivery_ids = fields.Many2many(
        'amanat.extract_delivery',
        string='Платежка',
        tracking=True,
        domain="[('direction_choice', '=', 'gold_deal')]"  # добавляем домен для фильтрации по золотым сделкам
    )

    # 29. Ордеры – связь с ордерами (многие ко многим)
    order_ids = fields.Many2many(
        'amanat.order',
        string='Ордеры',
        tracking=True
    )

    # 30. Покупатель – связь с Контрагентами
    buyer_id = fields.Many2one(
        'amanat.contragent',
        string='Покупатель',
        tracking=True
    )

    # 31. Хеш
    hash_flag = fields.Boolean(string='Хеш', default=False, tracking=True)

    # --- Compute методы для Rollup/Formula полей ---

    @api.depends('partner_ids.pure_weight')
    def _compute_pure_weight_sum(self):
        for rec in self:
            rec.pure_weight_sum = sum(rec.partner_ids.mapped('pure_weight'))

    @api.depends('partner_ids.amount_rub')
    def _compute_purchase_total_rub(self):
        for rec in self:
            rec.purchase_total_rub = sum(rec.partner_ids.mapped('amount_rub'))

    @api.depends('partner_ids.purchase_amount_dollar')
    def _compute_purchase_total_dollar(self):
        for rec in self:
            rec.purchase_total_dollar = sum(rec.partner_ids.mapped('purchase_amount_dollar'))

    @api.depends('partner_ids.total_expenses')
    def _compute_expenses(self):
        for rec in self:
            rec.expenses = sum(rec.partner_ids.mapped('total_expenses'))

    @api.depends('partner_ids.service_amount')
    def _compute_service(self):
        for rec in self:
            rec.service = sum(rec.partner_ids.mapped('service_amount'))

    @api.depends('partner_ids.bank_amount')
    def _compute_bank_sum(self):
        for rec in self:
            rec.bank_sum = sum(rec.partner_ids.mapped('bank_amount'))

    @api.depends('partner_ids.bank_kb_amount')
    def _compute_bank_kb(self):
        for rec in self:
            rec.bank_kb = sum(rec.partner_ids.mapped('bank_kb_amount'))

    @api.depends('partner_ids.courier_amount')
    def _compute_courier(self):
        for rec in self:
            rec.courier = sum(rec.partner_ids.mapped('courier_amount'))

    @api.depends('partner_ids.purchase_usdt')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.partner_ids.mapped('purchase_usdt'))

    @api.depends('partner_ids.sale_amount_aed')
    def _compute_sale_amount_aed(self):
        for rec in self:
            rec.sale_amount_aed = sum(rec.partner_ids.mapped('sale_amount_aed'))

    @api.depends('partner_ids.purchase_usdt')
    def _compute_sale_amount_usdt(self):
        for rec in self:
            rec.sale_amount_usdt = sum(rec.partner_ids.mapped('purchase_usdt'))

    @api.depends('purchase_total_rub', 'total_amount')
    def _compute_final_rate(self):
        for rec in self:
            rec.final_rate = rec.purchase_total_rub / rec.total_amount if rec.total_amount else 0

    @api.depends('purchase_total_rub', 'invoice_amount')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.purchase_total_rub - rec.invoice_amount

    @staticmethod
    def _prepare_currency_fields(currency_name: str, amount: float):
        """
        Полная матрица полей-сумм по валютам,
        возвращаем словарь для передачи ** в create().
        """
        data = {
            'sum_rub': 0, 'sum_rub_cash': 0,
            'sum_usd': 0, 'sum_usd_cash': 0,
            'sum_usdt': 0,
            'sum_cny': 0, 'sum_cny_cash': 0,
            'sum_eur': 0, 'sum_eur_cash': 0,
            'sum_aed': 0, 'sum_aed_cash': 0,
            'sum_thb': 0, 'sum_thb_cash': 0,
        }
        mapping = {
            'RUB': 'sum_rub',
            'RUB_CASH': 'sum_rub_cash',
            'USD': 'sum_usd',
            'USD_CASH': 'sum_usd_cash',
            'USDT': 'sum_usdt',
            'CNY': 'sum_cny',
            'CNY_CASH': 'sum_cny_cash',
            'EUR': 'sum_eur',
            'EUR_CASH': 'sum_eur_cash',
            'AED': 'sum_aed',
            'AED_CASH': 'sum_aed_cash',
            'THB': 'sum_thb',
            'THB_CASH': 'sum_thb_cash',
        }
        key = mapping.get(currency_name.upper())
        if key:
            data[key] = amount
        return data

    # "Золото вход" контейнеры
    @api.model
    def create(self, vals):
        rec = super(GoldDeal, self).create(vals)
        if vals.get('conduct_in') and rec.status == 'open':
            rec._action_conduct_in()
        if vals.get('conduct_out'):
            rec._action_conduct_out()
        if vals.get('mark_for_deletion'):
            rec._action_delete()
            rec.status = 'archived'
        return rec

    def write(self, vals):
        res = super(GoldDeal, self).write(vals)

        # обрабатываем каждую записанную сделку
        if vals.get('conduct_in'):
            for rec in self:
                rec._action_conduct_in()

        if vals.get('conduct_out'):
            for rec in self:
                rec._action_conduct_out()

        if vals.get('mark_for_deletion'):
            for rec in self:
                rec._action_delete()
                rec.status = 'archived'
                
        return res

    def _action_conduct_in(self):
        """
        Автоматизация входа в сделку "Золото":
        - Антидюп: удаляет старые ордера, контейнеры и сверки
        - Создаёт новые ордера, контейнеры и сверки для каждого партнёра
        - Создаёт финальный ордер «Золото → Вита»
        """
        for rec in self:
            # === Антидюп: удаляем прошлые записи ===
            existing_orders = rec.order_ids
            if existing_orders:
                for order in existing_orders:
                    if order.sverka_ids:
                        order.sverka_ids.unlink()
                    if order.money_ids:
                        order.money_ids.unlink()
                existing_orders.unlink()
            rec.order_ids = [(5, 0, 0)]
            for partner in rec.partner_ids:
                partner.order_ids = [(5, 0, 0)]

            # === Справочные записи ===
            Contr = self.env['amanat.contragent']
            Pay = self.env['amanat.payer']
            Wal = self.env['amanat.wallet']
            gold_ctr = Contr.search([('name', '=', 'Золото')], limit=1)
            vita_ctr = Contr.search([('name', '=', 'Вита')], limit=1)
            # найдём или создадим «Золото» и «Вита»
            gold_ctr = Contr.search([('name', '=', 'Золото')], limit=1)
            if not gold_ctr:
                gold_ctr = Contr.create({'name': 'Золото'})
            vita_ctr = Contr.search([('name', '=', 'Вита')], limit=1)
            if not vita_ctr:
                vita_ctr = Contr.create({'name': 'Вита'})

            gold_pay = Pay.search([('name', '=', 'Золото')], limit=1)
            if not gold_pay:
                gold_pay = Pay.create({'name': 'Золото'})
            vita_pay = Pay.search([('name', '=', 'Вита')], limit=1)
            if not vita_pay:
                vita_pay = Pay.create({'name': 'Вита'})

            gold_wal = Wal.search([('name', '=', 'Золото')], limit=1)

            total_amt = 0.0
            Order = self.env['amanat.order']
            Money = self.env['amanat.money']
            Recon = self.env['amanat.reconciliation']

            # === Создаём ордера и связанные записи для каждого партнёра ===
            for partner in rec.partner_ids:
                ctr = partner.partner_id
                pay = partner.payer_id or Pay.search([('contragents_ids', 'in', ctr.id)], limit=1)
                amt = partner.partner_invoice_amount
                if not (ctr and pay and amt):
                    _logger.error('Пропускаем партнёра %s – недостаточно данных', partner.id)
                    continue
                ord = Order.create({
                    'date': rec.date,
                    'partner_1_id': ctr.id,
                    'payer_1_id': pay.id,
                    'partner_2_id': gold_ctr.id,
                    'payer_2_id': gold_pay.id,
                    'amount': amt,
                    'currency': 'rub',
                    'type': 'transfer',
                    'comment': 'Вход в сделку Золото',
                })
                rec.order_ids |= ord
                partner.order_ids |= ord
                total_amt += amt

                # Контейнер денег – положительный
                Money.create({
                    'date': rec.date,
                    'partner_id': ctr.id,
                    'currency': 'rub',
                    'amount': amt,
                    'sum_rub': amt,
                    'state': 'positive',
                    'wallet_id': gold_wal.id,
                    'order_id': [(4, ord.id)],
                })

                if total_amt:
                # финальная сверка – только если total_amt != 0 и payers найдены
                    Recon.create({
                        'date': rec.date,
                        'partner_id': ctr.id,
                        'currency': 'rub',
                        'sum': amt,
                        'sum_rub': amt,
                        'sender_id': [(4, pay.id)],
                        'receiver_id': [(4, gold_pay.id)],
                        'wallet_id': gold_wal.id,
                        'order_id': [(4, ord.id)],
                    })

            # === Финальный ордер Золото → Вита ===
            ord_fin = Order.create({
                'date': rec.date,
                'partner_1_id': gold_ctr.id,
                'payer_1_id': gold_pay.id,
                'partner_2_id': vita_ctr.id,
                'payer_2_id': vita_pay.id,
                'amount': total_amt,
                'currency': 'rub',
                'type': 'transfer',
                'comment': 'Вход в сделку Золото',
            })
            rec.order_ids |= ord_fin

            # Контейнер денег – долг для Вита
            Money.create({
                'date': rec.date,
                'partner_id': vita_ctr.id,
                'currency': 'rub',
                'amount': -total_amt,
                'sum_rub': -total_amt,
                'state': 'debt',
                'wallet_id': gold_wal.id,
                'order_id': [(4, ord_fin.id)],
            })

            # Сверка для Вита
            Recon.create({
                'date': rec.date,
                'partner_id': vita_ctr.id,
                'currency': 'rub',
                'sum': -total_amt,
                'sum_rub': -total_amt,
                'sender_id': [(4, gold_pay.id)],
                'receiver_id': [(4, vita_pay.id)],
                'wallet_id': gold_wal.id,
                'order_id': [(4, ord_fin.id)],
            })

            rec.conduct_in = False

    def _action_conduct_out(self):
        """
        Перенос автоматизации «Золото → Вита» из Airtable.
        Создаёт долговые/положительные контейнеры и сверку
        по каждому ордеру, где Контрагент 2 = Вита.
        """
        Contr = self.env['amanat.contragent']
        Order = self.env['amanat.order']
        Money = self.env['amanat.money']
        Recon = self.env['amanat.reconciliation']
        Wallet = self.env['amanat.wallet']
        Extract = self.env['amanat.extract_delivery']

        # справочные записи
        vita_ctr = Contr.search([('name', '=', 'Вита')], limit=1)
        if not vita_ctr:
            vita_ctr = Contr.create({'name': 'Вита'})

        rub_wallet = Wallet.search([('name', '=', 'Золото')], limit=1)
        if not rub_wallet:
            raise UserError('Кошелёк "Золото" не найден, создайте его перед обработкой выхода.')

        for rec in self:
            # антидюп: если vita_posting уже true – выходим
            if rec.vita_posting:
                _logger.info('Сделка %s уже проведена (выход)', rec.name)
                continue

            # --- платежка ---
            if not rec.extract_delivery_ids:
                raise UserError('У сделки нет привязанной платежки.')
            statement = rec.extract_delivery_ids[0]  # берём первую
            if statement.recipient_id != vita_ctr:
                _logger.info('Получатель платежки не Вита – выход не требуется.')
                continue
            if not statement.date:
                raise UserError('В платежке не указана дата.')

            amount = statement.amount
            if not amount:
                raise UserError('В платежке отсутствует сумма.')

            # --- отбор ордеров Золото → Вита ---
            domain = [
                ('id', 'in', rec.order_ids.ids),
                ('partner_2_id', '=', vita_ctr.id)
            ]
            rel_orders = Order.search(domain)
            _logger.info('Сделка %s: найдено %s связанных ордеров для выхода.',
                         rec.name, len(rel_orders))

            for ord in rel_orders:
                contr1 = ord.partner_1_id
                if not contr1:
                    _logger.warning('Ордер %s без Контрагента 1 – пропуск', ord.id)
                    continue
                wallet_1 = ord.wallet_1_id or rub_wallet  # поправьте, если поле называется иначе

                # комментарий
                ord.comment = 'Перевод денег на Виту по сделке Золото'

                # --- Money контейнеры ---
                Money.create({
                    'date': statement.date,
                    'partner_id': contr1.id,
                    'currency': 'rub',
                    'amount': -amount,
                    'sum_rub': -amount,
                    'state': 'debt',
                    'wallet_id': wallet_1.id,
                    'order_id': [(4, ord.id)],
                })
                Money.create({
                    'date': statement.date,
                    'partner_id': vita_ctr.id,
                    'currency': 'rub',
                    'amount': amount,
                    'sum_rub': amount,
                    'state': 'positive',
                    'wallet_id': wallet_1.id,
                    'order_id': [(4, ord.id)],
                })

                # --- Сверка ---
                payer1 = ord.payer_1_id
                payer2 = ord.payer_2_id
                Recon.create({
                    'date': statement.date,
                    'partner_id': contr1.id,
                    'currency': 'rub',
                    'sum': -amount,
                    **self._prepare_currency_fields('RUB', -amount),
                    'sender_id': [(4, payer1.id)] if payer1 else False,
                    'receiver_id': [(4, payer2.id)] if payer2 else False,
                    'wallet_id': wallet_1.id,
                    'order_id': [(4, ord.id)],
                })
                Recon.create({
                    'date': statement.date,
                    'partner_id': vita_ctr.id,
                    'currency': 'rub',
                    'sum': amount,
                    **self._prepare_currency_fields('RUB', amount),
                    'sender_id': [(4, payer1.id)] if payer1 else False,
                    'receiver_id': [(4, payer2.id)] if payer2 else False,
                    'wallet_id': wallet_1.id,
                    'order_id': [(4, ord.id)],
                })

            # по окончании – сбрасываем флаг, помечаем, что проведено
            rec.conduct_out = False
            rec.vita_posting = True
            _logger.info('Сделка %s: выход успешно проведён.', rec.name)

    def _action_delete(self):
        for rec in self:
            for order in rec.order_ids:
                order.money_ids.unlink()
                order.sverka_ids.unlink()
                order.unlink()
            rec.order_ids = [(5, 0, 0)]
            rec.mark_for_deletion = False

    
