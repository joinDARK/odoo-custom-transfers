# models/transfer.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Transfer(models.Model, AmanatBaseModel):
    _name = 'amanat.transfer'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Перевод'
    
    name = fields.Char(
        string='Номер заявки',
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.transfer.sequence'),
        readonly=True
    )
    state = fields.Selection(
        [('open', 'Открыта'), ('archive', 'Архив'), ('close', 'Закрыта')],
        string='Статус',
        default='open',
        tracking=True
    )
    date = fields.Date(string='Дата', default=fields.Date.today, tracking=True)
    
    currency = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'), ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
            ('usdt', 'USDT'), ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'), ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
        ],
        string='Валюта',
        default='rub',
        tracking=True
    )
    amount = fields.Float(string='Сумма', tracking=True)

    sender_id = fields.Many2one(
        'amanat.contragent', 
        string='Отправитель',
        tracking=True,
    )
    sender_payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик отправителя',
        tracking=True,
        domain="[('contragents_ids', 'in', sender_id)]"
    )
    sender_wallet_id = fields.Many2one('amanat.wallet', string='Кошелек отправителя', tracking=True)

    receiver_id = fields.Many2one(
        'amanat.contragent', 
        string='Получатель',
        tracking=True,
    )

    hash = fields.Boolean(string='Хеш', default=False, tracking=True)

    receiver_payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик получателя',
        tracking=True,
        domain="[('contragents_ids', 'in', receiver_id)]"
    )
    receiver_wallet_id = fields.Many2one('amanat.wallet', string='Кошелек получателя', tracking=True)

    # Royalti
    royalti_Transfer = fields.Boolean(string='Провести роялти', default=False, tracking=True)
    royalty_percent_1 = fields.Float(string="Процент роялти 1", tracking=True)
    royalty_percent_2 = fields.Float(string="Процент роялти 2", tracking=True)
    royalty_percent_3 = fields.Float(string="Процент роялти 3", tracking=True)
    royalty_percent_4 = fields.Float(string="Процент роялти 4", tracking=True)
    royalty_percent_5 = fields.Float(string="Процент роялти 5", tracking=True)

    royalty_recipient_1 = fields.Many2one('amanat.contragent', string="Получатель роялти 1", tracking=True)
    royalty_recipient_2 = fields.Many2one('amanat.contragent', string="Получатель роялти 2", tracking=True)
    royalty_recipient_3 = fields.Many2one('amanat.contragent', string="Получатель роялти 3", tracking=True)
    royalty_recipient_4 = fields.Many2one('amanat.contragent', string="Получатель роялти 4", tracking=True)
    royalty_recipient_5 = fields.Many2one('amanat.contragent', string="Получатель роялти 5", tracking=True)

    # Delete
    delete_Transfer = fields.Boolean(string='Удалить поле', default=False, tracking=True)

    # Create
    create_order = fields.Boolean(string='Создать', default=False, tracking=True)
    is_complex = fields.Boolean(string='Сложный перевод', default=False, tracking=True)
    intermediary_1_id = fields.Many2one('amanat.contragent', string='Посредник 1', tracking=True)
    intermediary_1_payer_id = fields.Many2one(
        'amanat.payer', 
        string='Плательщик посредника 1', 
        tracking=True,
        domain="[('contragents_ids', 'in', intermediary_1_id)]"
    )
    intermediary_1_wallet_id = fields.Many2one('amanat.wallet', string='Кошелек посредника 1', tracking=True)
    intermediary_1_sum = fields.Float(
        string='Сумма 1 посредника',
        tracking=True,
        store=True,
        compute='_compute_intermediary_1_sum', 
    )
    intermediary_1_commission_percent = fields.Float(
        string='Процент комиссии по отправке Посредник 1', 
        tracking=True
    )

    intermediary_2_id = fields.Many2one('amanat.contragent', string='Посредник 2', tracking=True)
    intermediary_2_payer_id = fields.Many2one(
        'amanat.payer', 
        string='Плательщик посредника 2', 
        tracking=True,
        domain="[('contragents_ids', 'in', intermediary_2_id)]"
    )
    intermediary_2_wallet_id = fields.Many2one('amanat.wallet', string='Кошелек посредника 2', tracking=True)
    intermediary_2_commission_percent = fields.Float(
        string='Процент комиссии по отправке Посредник 2', 
        tracking=True
    )
    intermediary_2_sum = fields.Float(
        string='Сумма 2 посредника',
        tracking=True,
        store=True,
        compute='_compute_intermediary_2_sum',
    )

    sending_commission_percent = fields.Float(string='Процент комиссии по отправке', tracking=True)

    order_ids = fields.Many2many(
        'amanat.order',
        'amanat_transfer_order_rel',
        'transfer_id',
        'order_id',
        tracking=True,
        string="Ордера",
        ondelete='cascade'
    )

    # Комментарии
    comment = fields.Text(string='Комментарии', tracking=True)

    manager_id = fields.Many2one('res.users', string='Manager', tracking=True, default=lambda self: self.env.user.id)
    inspector_id = fields.Many2one('res.users', string='Inspector', tracking=True)

    @api.onchange('sender_id')
    def _onchange_sender_id(self):
        if self.sender_id:
            payer = self.env['amanat.payer'].search(
                [('contragents_ids', 'in', self.sender_id.id)], limit=1)
            self.sender_payer_id = payer.id if payer else False
        else:
            self.sender_payer_id = False
    
    @api.onchange('receiver_id')
    def _onchange_receiver_id(self):
        if self.receiver_id:
            payer = self.env['amanat.payer'].search(
                [('contragents_ids', 'in', self.receiver_id.id)], limit=1)
            self.receiver_payer_id = payer.id if payer else False
        else:
            self.receiver_payer_id = False

    @api.onchange('intermediary_1_id')
    def _onchange_intermediary_1_id(self):
        if self.intermediary_1_id:
            payer = self.env['amanat.payer'].search(
                [('contragents_ids', 'in', self.intermediary_1_id.id)], limit=1)
            self.intermediary_1_payer_id = payer.id if payer else False
        else:
            self.intermediary_1_payer_id = False

    @api.onchange('intermediary_2_id')
    def _onchange_intermediary_2_id(self):
        if self.intermediary_2_id:
            payer = self.env['amanat.payer'].search(
                [('contragents_ids', 'in', self.intermediary_2_id.id)], limit=1)
            self.intermediary_2_payer_id = payer.id if payer else False
        else:
            self.intermediary_2_payer_id = False

    # Новые формулы для вычисления суммы посредников
    @api.depends('amount', 'intermediary_1_commission_percent')
    def _compute_intermediary_1_sum(self):
        for record in self:
            # Сумма 1 посредника = {Сумма} - ({Сумма} * {Процент комиссии по отправке Посредник 1} / 100)
            record.intermediary_1_sum = record.amount - (record.amount * record.intermediary_1_commission_percent) if record.amount else 0.0

    @api.depends('intermediary_1_sum', 'intermediary_2_commission_percent')
    def _compute_intermediary_2_sum(self):
        for record in self:
            # Сумма 2 посредника = {Сумма 1 посредника} - ({Сумма 1 посредника} * {Процент комиссии по отправке Посредник 2} / 100)
            record.intermediary_2_sum = record.intermediary_1_sum - (record.intermediary_1_sum * record.intermediary_2_commission_percent) if record.intermediary_1_sum else 0.0

    def create_transfer_orders(self):
        for record in self:
            # Удаляем старые ордера (через каскад удалятся и контейнеры, и сверки)
            if record.order_ids:
                record._delete_related_records()

            # Определяем, какой сценарий: без посредников, 1 посредник или 2
            if record.is_complex:
                if record.intermediary_1_id and record.intermediary_2_id:
                    self._create_two_intermediary_transfer(record)
                elif record.intermediary_1_id and not record.intermediary_2_id:
                    self._create_one_intermediary_transfer(record)
                else:
                    self._create_simple_transfer(record)
            else:
                self._create_simple_transfer(record)

    # ================================
    # 1) Без посредников
    # ================================
    def _create_simple_transfer(self, record):
        order = self.env['amanat.order'].create({
            'date': record.date,
            'type': 'transfer',
            'partner_1_id': record.sender_id.id,
            'partner_2_id': record.receiver_id.id,
            'wallet_1_id': record.sender_wallet_id.id,
            'wallet_2_id': record.receiver_wallet_id.id,
            'payer_1_id': record.sender_payer_id.id,
            'payer_2_id': record.receiver_payer_id.id,
            'currency': record.currency,
            'amount': record.amount,
            'comment': record.comment,
            'operation_percent': record.sending_commission_percent,
            # Используем команду для Many2many: (6, 0, [record.id])
            'transfer_id': [(6, 0, [record.id])],
        })
        
        amount_1, amount_2 = self._calculate_amounts(record.amount, record.sending_commission_percent)

        # Деньги/Сверки: сначала списываем со счета отправителя, затем зачисляем получателю
        self._create_money_and_reconciliation(
            order, record.sender_wallet_id, record.sender_id,
            -amount_1, record.sender_payer_id, record.receiver_payer_id
        )
        self._create_money_and_reconciliation(
            order, record.receiver_wallet_id, record.receiver_id,
            amount_2, record.sender_payer_id, record.receiver_payer_id
        )

    # ================================
    # 2) Один посредник
    # ================================
    def _create_one_intermediary_transfer(self, record):
        """
        Сценарий:
        A) Отправитель -> Посредник_1 (сумма = record.amount)
        B) Посредник_1 -> Получатель (сумма = record.intermediary_1_sum)
        """
        # A) Отправитель -> Посредник_1
        order_a = self.env['amanat.order'].create({
            'date': record.date,
            'type': 'transfer',
            'partner_1_id': record.sender_id.id,
            'partner_2_id': record.intermediary_1_id.id,
            'wallet_1_id': record.sender_wallet_id.id,
            'wallet_2_id': record.intermediary_1_wallet_id.id,
            'payer_1_id': record.sender_payer_id.id,
            'payer_2_id': record.intermediary_1_payer_id.id,
            'currency': record.currency,
            'amount': record.amount,
            'comment': record.comment,
            'operation_percent': record.sending_commission_percent,
            'transfer_id': [(6, 0, [record.id])],
        })

        a1, a2 = self._calculate_amounts(record.amount, record.sending_commission_percent)
        self._create_money_and_reconciliation(
            order_a, record.sender_wallet_id, record.sender_id,
            -a1, record.sender_payer_id, record.intermediary_1_payer_id
        )
        self._create_money_and_reconciliation(
            order_a, record.intermediary_1_wallet_id, record.intermediary_1_id,
            a2, record.sender_payer_id, record.intermediary_1_payer_id
        )

        # B) Посредник_1 -> Получатель (только если есть сумма для перевода)
        if record.intermediary_1_sum and record.intermediary_1_sum > 0:
            order_b = self.env['amanat.order'].create({
                'date': record.date,
                'type': 'transfer',
                'partner_1_id': record.intermediary_1_id.id,
                'partner_2_id': record.receiver_id.id,
                'wallet_1_id': record.intermediary_1_wallet_id.id,
                'wallet_2_id': record.receiver_wallet_id.id,
                'payer_1_id': record.intermediary_1_payer_id.id,
                'payer_2_id': record.receiver_payer_id.id,
                'currency': record.currency,
                'amount': record.intermediary_1_sum,
                'comment': record.comment,
                'operation_percent': record.sending_commission_percent,
                'transfer_id': [(6, 0, [record.id])],
            })
            self._create_money_and_reconciliation(
                order_b, record.intermediary_1_wallet_id, record.intermediary_1_id,
                -record.intermediary_1_sum, record.intermediary_1_payer_id, record.receiver_payer_id
            )
            self._create_money_and_reconciliation(
                order_b, record.receiver_wallet_id, record.receiver_id,
                record.intermediary_1_sum, record.intermediary_1_payer_id, record.receiver_payer_id
            )

    # ================================
    # 3) Два посредника
    # ================================
    def _create_two_intermediary_transfer(self, record):
        """
        Сценарий:
        A) Отправитель -> Посредник_1 (сумма = record.amount)
        B) Посредник_1 -> Посредник_2 (сумма = record.intermediary_1_sum)
        C) Посредник_2 -> Получатель (сумма = record.intermediary_2_sum)
        """

        # A) Отправитель -> Посредник_1
        order_a = self.env['amanat.order'].create({
            'date': record.date,
            'type': 'transfer',
            'partner_1_id': record.sender_id.id,
            'partner_2_id': record.intermediary_1_id.id,
            'wallet_1_id': record.sender_wallet_id.id,
            'wallet_2_id': record.intermediary_1_wallet_id.id,
            'payer_1_id': record.sender_payer_id.id,
            'payer_2_id': record.intermediary_1_payer_id.id,
            'currency': record.currency,
            'amount': record.amount,
            'comment': record.comment,
            'operation_percent': record.sending_commission_percent,
            'transfer_id': [(6, 0, [record.id])],
        })
        a1, a2 = self._calculate_amounts(record.amount, record.sending_commission_percent)
        self._create_money_and_reconciliation(
            order_a, record.sender_wallet_id, record.sender_id,
            -a1, record.sender_payer_id, record.intermediary_1_payer_id
        )
        self._create_money_and_reconciliation(
            order_a, record.intermediary_1_wallet_id, record.intermediary_1_id,
            a2, record.sender_payer_id, record.intermediary_1_payer_id
        )

        # B) Посредник_1 -> Посредник_2
        if record.intermediary_1_sum and record.intermediary_1_sum > 0:
            order_b = self.env['amanat.order'].create({
                'date': record.date,
                'type': 'transfer',
                'partner_1_id': record.intermediary_1_id.id,
                'partner_2_id': record.intermediary_2_id.id,
                'wallet_1_id': record.intermediary_1_wallet_id.id,
                'wallet_2_id': record.intermediary_2_wallet_id.id,
                'payer_1_id': record.intermediary_1_payer_id.id,
                'payer_2_id': record.intermediary_2_payer_id.id,
                'currency': record.currency,
                'amount': record.intermediary_1_sum,
                'comment': record.comment,
                'operation_percent': record.sending_commission_percent,
                'transfer_id': [(6, 0, [record.id])],
            })
            b1, b2 = self._calculate_amounts(record.intermediary_1_sum, record.sending_commission_percent)
            self._create_money_and_reconciliation(
                order_b, record.intermediary_1_wallet_id, record.intermediary_1_id,
                -b1, record.intermediary_1_payer_id, record.intermediary_2_payer_id
            )
            self._create_money_and_reconciliation(
                order_b, record.intermediary_2_wallet_id, record.intermediary_2_id,
                b2, record.intermediary_1_payer_id, record.intermediary_2_payer_id
            )

        # C) Посредник_2 -> Получатель
        if record.intermediary_2_sum and record.intermediary_2_sum > 0:
            order_c = self.env['amanat.order'].create({
                'date': record.date,
                'type': 'transfer',
                'partner_1_id': record.intermediary_2_id.id,
                'partner_2_id': record.receiver_id.id,
                'wallet_1_id': record.intermediary_2_wallet_id.id,
                'wallet_2_id': record.receiver_wallet_id.id,
                'payer_1_id': record.intermediary_2_payer_id.id,
                'payer_2_id': record.receiver_payer_id.id,
                'currency': record.currency,
                'amount': record.intermediary_2_sum,
                'comment': record.comment,
                'operation_percent': record.sending_commission_percent,
                'transfer_id': [(6, 0, [record.id])],
            })
            c1, c2 = self._calculate_amounts(record.intermediary_2_sum, record.sending_commission_percent)
            self._create_money_and_reconciliation(
                order_c, record.intermediary_2_wallet_id, record.intermediary_2_id,
                -c1, record.intermediary_2_payer_id, record.receiver_payer_id
            )
            self._create_money_and_reconciliation(
                order_c, record.receiver_wallet_id, record.receiver_id,
                c2, record.intermediary_2_payer_id, record.receiver_payer_id
            )

    # ========================================
    # Создание записей Money и Reconciliation
    # ========================================
    def _create_money_and_reconciliation(self, order, wallet, partner, amount, sender_payer, receiver_payer):
        currency_fields = self._get_currency_fields(order.currency, amount)

        # Создание записи в модели amanat.money
        self.env['amanat.money'].create({
            'date': order.date,
            'wallet_id': wallet.id,
            'partner_id': partner.id,
            'currency': order.currency,
            'amount': amount,
            'order_id': [(6, 0, [order.id])],
            'state': 'positive' if amount > 0 else 'debt',
            **currency_fields
        })

        # Создание записи в модели amanat.reconciliation
        self.env['amanat.reconciliation'].create({
            'date': order.date,
            'partner_id': partner.id,
            'currency': order.currency,
            'sum': amount,
            'order_id': [(6, 0, [order.id])],
            'wallet_id': wallet.id,
            'sender_id': [(6, 0, [sender_payer.id])] if sender_payer else [(6, 0, [])],
            'receiver_id': [(6, 0, [receiver_payer.id])] if receiver_payer else [(6, 0, [])],
            **currency_fields
        })

    def _get_currency_fields(self, currency, amount):
        mapping = {
            'rub': 'sum_rub', 'usd': 'sum_usd', 'usdt': 'sum_usdt', 'cny': 'sum_cny', 'euro': 'sum_euro',
            'aed': 'sum_aed', 'thb': 'sum_thb',
            'rub_cashe': 'sum_rub_cashe', 'usd_cashe': 'sum_usd_cashe', 'euro_cashe': 'sum_euro_cashe',
            'cny_cashe': 'sum_cny_cashe', 'aed_cashe': 'sum_aed_cashe', 'thb_cashe': 'sum_thb_cashe'
        }
        field = mapping.get(currency)
        return {field: amount} if field else {}

    def _calculate_amounts(self, amount, percent):
        amount_1 = amount
        amount_2 = amount - (amount * percent / 100) if percent else amount
        return amount_1, amount_2

    def write(self, vals):
        if self.env.context.get('skip_automation'):
            return super(Transfer, self).write(vals)

        res = super(Transfer, self).write(vals)

        # Удаление
        to_archive = self.filtered(lambda rec: rec.delete_Transfer)
        if to_archive:
            for rec in to_archive:
                if not rec.order_ids:
                    rec.create_transfer_orders()
                rec._delete_related_records()
            to_archive.with_context(skip_automation=True).write({'delete_Transfer': False, 'state': 'archive'})

        # Роялти
        to_process_royalty = self.filtered(lambda rec: rec.royalti_Transfer)
        if to_process_royalty:
            for rec in to_process_royalty:
                rec._process_royalty_distribution()
            to_process_royalty.with_context(skip_automation=True).write({'royalti_Transfer': False})

        # Создание
        to_create = self.filtered(lambda rec: rec.create_order and rec.state == 'open')
        if to_create:
            for rec in to_create:
                rec.create_transfer_orders()
            to_create.with_context(skip_automation=True).write({'create_order': False})

        return res
    
    def _delete_related_records(self):
        for transfer in self:
            for order in transfer.order_ids:
                # Найдём связанные деньги
                moneys = self.env['amanat.money'].search([('order_id', 'in', order.ids)])
                for money in moneys:
                    money.writeoff_ids.unlink()
                    money.unlink()

                # Найдём связанные сверки
                reconciliations = self.env['amanat.reconciliation'].search([('order_id', 'in', order.ids)])
                reconciliations.unlink()

                # Удаляем сам ордер
                order.unlink()
        
    def _process_royalty_distribution(self):
        royalty_contragent = self.env['amanat.contragent'].search([('name', '=', 'Роялти')], limit=1)
        royalty_payer = self.env['amanat.payer'].search([
            ('contragents_ids', 'in', royalty_contragent.id)
        ], limit=1) if royalty_contragent else self.amount
        old_royalty_orders = self.env['amanat.order'].search([
            ('transfer_id', '=', self.id),
            ('type', '=', 'royalty')
        ])
        for order in old_royalty_orders:
            self.env['amanat.money'].search([('order_id', 'in', order.ids)]).unlink()
            self.env['amanat.reconciliation'].search([('order_id', 'in', order.ids)]).unlink()
            order.unlink()

        for i in range(1, 6):
            recipient = getattr(self, f'royalty_recipient_{i}')
            percent = getattr(self, f'royalty_percent_{i}')
            if recipient and percent and self.amount:
                royalty_sum = round(self.amount * percent, 2)
                royalty_sum = -abs(royalty_sum)

                recipient_payer = self.env['amanat.payer'].search([
                   ('contragents_ids', 'in', recipient.id)
                ], limit=1)

                royalty_order = self.env['amanat.order'].create({
                    'date': self.date,
                    'type': 'transfer',
                    'partner_1_id': royalty_contragent.id if royalty_contragent else False,
                    'partner_2_id': recipient.id,
                    'wallet_1_id': self.receiver_wallet_id.id,
                    'wallet_2_id': self.receiver_wallet_id.id,
                    'payer_1_id': royalty_payer.id if royalty_payer else False,
                    'payer_2_id': recipient_payer.id if recipient_payer else False,
                    'currency': self.currency,
                    'comment': self.comment,
                    'amount': royalty_sum,
                    'transfer_id': [(6, 0, [self.id])],
                })

                currency_fields = self._get_currency_fields(self.currency, royalty_sum)

                self.env['amanat.money'].create({
                    'royalty': True,
                    'date': self.date,
                    'wallet_id': self.receiver_wallet_id.id,
                    'partner_id': recipient.id,
                    'currency': self.currency,
                    'amount': royalty_sum,
                    'order_id': [(6, 0, [royalty_order.id])],
                    'state': 'debt',
                    **currency_fields
                })

                self.env['amanat.reconciliation'].create({
                    'date': self.date,
                    'partner_id': recipient.id,
                    'currency': self.currency,
                    'sum': royalty_sum,
                    'order_id': [(6, 0, [royalty_order.id])],
                    'wallet_id': self.receiver_wallet_id.id,
                    'sender_id': [(6, 0, [royalty_payer.id])] if royalty_payer else [(6, 0, [])],
                    'receiver_id': [(6, 0, [recipient_payer.id])] if recipient_payer else [(6, 0, [])],
                    **currency_fields
                })

    @api.model
    def create(self, vals):
        # Найдём или создадим кошелёк «Неразмеченные»
        Wallet = self.env['amanat.wallet']
        unmarked = Wallet.search([('name', '=', 'Неразмеченные')], limit=1)
        if not unmarked:
            unmarked = Wallet.create({'name': 'Неразмеченные'})
        # Если в vals не задан кошелёк отправителя/получателя — подставляем
        if not vals.get('sender_wallet_id'):
            vals['sender_wallet_id'] = unmarked.id
        if not vals.get('receiver_wallet_id'):
            vals['receiver_wallet_id'] = unmarked.id
        if not vals.get('intermediary_2_wallet_id'):
            vals['intermediary_2_wallet_id'] = unmarked.id
        if not vals.get('intermediary_1_wallet_id'):
            vals['intermediary_1_wallet_id'] = unmarked.id
        return super(Transfer, self).create(vals)