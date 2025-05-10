from odoo import models, fields, api
from .base_model import AmanatBaseModel


class Reserve(models.Model, AmanatBaseModel):
    _name = 'amanat.reserve'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Валютный резерв'

    name = fields.Char(
        string='Номер сделки',
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.reserve.sequence'),
        readonly=True
    )
    status = fields.Selection(
        [('open', 'Открыта'), ('archive', 'Архив'), ('close', 'Закрыта')],
        string='Статус',
        default='open',
        tracking=True
    )
    today_date = fields.Date(string="Дата", default=fields.Date.context_today, tracking=True)
    currency = fields.Selection([
        ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'), ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
        ('usdt', 'USDT'), ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
        ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'), ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
        ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
    ], string='Валюта', default='rub', tracking=True)
    amount = fields.Float(string="Сумма", tracking=True, digits=(16, 2))
    sender_id = fields.Many2one('amanat.contragent', string='Отправитель', tracking=True)
    sender_payer_id = fields.Many2one(
        'amanat.payer', string='Плательщик отправителя', tracking=True,
        domain="[('contragents_ids','in',sender_id)]"
    )
    commision_percent_1 = fields.Float(string="Процент комиссии по отправке", tracking=True)
    receiver_id = fields.Many2one('amanat.contragent', string='Получатель', tracking=True)
    receiver_payer_id = fields.Many2one(
        'amanat.payer', string='Плательщик получателя', tracking=True,
        domain="[('contragents_ids','in',receiver_id)]"
    )
    commision_percent_2 = fields.Float(string="Процент комиссии отправителя", tracking=True)

    commision_difference = fields.Float(
        string="Разница комиссии", compute="_compute_commission_difference", store=True, tracking=True
    )
    finally_result = fields.Float(
        string="Фин рез", compute="_compute_finally_result", store=True, tracking=True
    )

    has_royalti = fields.Boolean(string='Есть роялти', default=False, tracking=True)
    make_royalti = fields.Boolean(string='Провести роялти', default=False, tracking=True)
    royalty_recipient_1 = fields.Many2one('amanat.contragent', string="Получатель роялти", tracking=True)
    royalty_percent_1 = fields.Float(string="% первого", tracking=True)
    royalty_amount_1 = fields.Float(
        string="Сумма роялти 1", compute="_compute_royalty_amount_1", store=True, tracking=True
    )
    royalty_recipient_2 = fields.Many2one('amanat.contragent', string="Получатель роялти 2", tracking=True)
    royalty_percent_2 = fields.Float(string="% второго", tracking=True)
    royalty_amount_2 = fields.Float(
        string="Сумма роялти 2", compute="_compute_royalty_amount_2", store=True, tracking=True
    )

    order_ids = fields.Many2many(
        'amanat.order', 'amanat_order_reserve_rel', 'reserve_id', 'order_id',
        string="Ордеры", tracking=True
    )

    create_reserve = fields.Boolean(string='Создать', default=False, tracking=True)
    update_reserve = fields.Boolean(string='Изменить', default=False, tracking=True)
    delete_reserve = fields.Boolean(string='Удалить', default=False, tracking=True)
    complete_reserve = fields.Boolean(string='Провести', default=False, tracking=True)

    # Комментарий
    comment = fields.Text(
        related='order_ids.comment',
        string='Комментарии',
        readonly=True,
        store=True,
        tracking=True
    )

    @api.onchange('sender_id')
    def _onchange_sender_id(self):
        self.sender_payer_id = self.env['amanat.payer'].search(
            [('contragents_ids', 'in', self.sender_id.id)], limit=1
        ).id if self.sender_id else False

    @api.onchange('receiver_id')
    def _onchange_receiver_id(self):
        self.receiver_payer_id = self.env['amanat.payer'].search(
            [('contragents_ids', 'in', self.receiver_id.id)], limit=1
        ).id if self.receiver_id else False

    @api.depends('commision_percent_1', 'commision_percent_2')
    def _compute_commission_difference(self):
        for rec in self:
            rec.commision_difference = rec.commision_percent_1 - rec.commision_percent_2

    @api.depends('amount', 'commision_difference')
    def _compute_finally_result(self):
        for rec in self:
            rec.finally_result = rec.amount * rec.commision_difference if rec.amount else 0

    @api.depends('amount', 'royalty_percent_1')
    def _compute_royalty_amount_1(self):
        for rec in self:
            rec.royalty_amount_1 = rec.amount * rec.royalty_percent_1

    @api.depends('amount', 'royalty_percent_2')
    def _compute_royalty_amount_2(self):
        for rec in self:
            rec.royalty_amount_2 = rec.amount * rec.royalty_percent_2

    def write(self, vals):
        if self.env.context.get('skip_automation'):
            return super().write(vals)
        res = super().write(vals)
        for rec in self:
            # Создать
            if vals.get('create_reserve') or (not vals and rec.create_reserve):
                if rec.status == 'open':
                    rec._create_reserve_order()
                rec.with_context(skip_automation=True).write({'create_reserve': False})
            # Провести роялти
            if vals.get('make_royalti') or (not vals and rec.make_royalti):
                rec._process_royalty_distribution()
                rec.with_context(skip_automation=True).write({'make_royalti': False})
            # Провести (закрыть)
            if vals.get('complete_reserve') or (not vals and rec.complete_reserve):
                rec._complete_reserve()
                rec.with_context(skip_automation=True).write({
                    'complete_reserve': False,
                    'status': 'close'
                })
            # Удалить
            if vals.get('delete_reserve') or (not vals and rec.delete_reserve):
                rec._delete_related_records()
                rec.with_context(skip_automation=True).write({
                    'delete_reserve': False,
                    'status': 'archive'
                })
        return res

    def _create_reserve_order(self):
        self.ensure_one()
        self._delete_related_records()
        order = self.env['amanat.order'].create({
            'date': self.today_date,
            'type': 'transfer',
            'partner_1_id': self.sender_id.id,
            'partner_2_id': self.receiver_id.id,
            'wallet_1_id': self._get_default_wallet_id(),
            'wallet_2_id': self._get_default_wallet_id(),
            'payer_1_id': self.sender_payer_id.id,
            'payer_2_id': self.receiver_payer_id.id,
            'currency': self.currency,
            'amount': self.amount,
            'operation_percent': self.commision_percent_1,
            'our_percent': self.commision_percent_2,
            'reserve_ids': [(6, 0, [self.id])],
            'comment': self.comment,
        })
        # Рассчитываем чистое списание и чистое зачисление
        amount_out, amount_in = self._calculate_amounts(
            self.amount,
            self.commision_percent_1,
            self.commision_percent_2,
        )
        # У отправителя: долг (отрицательное)
        self._create_money_and_reconciliation(
            order, self.sender_id, -amount_out,
            self.sender_payer_id, self.receiver_payer_id
        )
        # У получателя: положительное
        self._create_money_and_reconciliation(
            order, self.receiver_id, amount_in,
            self.sender_payer_id, self.receiver_payer_id
        )

    def _calculate_amounts(self, amount, percent_out, percent_in):
        """
        Учёт того, что percent_* может храниться как доля (0.1) или как проценты (10).
        """
        # если ввод > 1, считаем его как проценты и делим на 100
        rate_out = percent_out / 100.0 if percent_out > 1 else percent_out
        rate_in  = percent_in  / 100.0 if percent_in  > 1 else percent_in
        net_out = amount * (1 - rate_out)
        net_in  = amount * (1 - rate_in)
        return net_out, net_in

    def _get_currency_fields(self, currency, amount):
        mapping = {
            'rub': 'sum_rub',       'rub_cashe': 'sum_rub_cashe',
            'usd': 'sum_usd',       'usd_cashe': 'sum_usd_cashe',
            'usdt': 'sum_usdt',
            'euro': 'sum_euro',     'euro_cashe': 'sum_euro_cashe',
            'cny': 'sum_cny',       'cny_cashe': 'sum_cny_cashe',
            'aed': 'sum_aed',       'aed_cashe': 'sum_aed_cashe',
            'thb': 'sum_thb',       'thb_cashe': 'sum_thb_cashe',
        }
        field = mapping.get(currency)
        return {field: amount} if field else {}

    def _create_money_and_reconciliation(self, order, partner, amount, sender_payer, receiver_payer):
        currency_fields = self._get_currency_fields(order.currency, amount)
        # Запись в Деньги
        self.env['amanat.money'].create({
            'date': order.date,
            'wallet_id': self._get_default_wallet().id,
            'partner_id': partner.id,
            'currency': order.currency,
            'amount': amount,
            'order_id': order.id,
            'state': 'positive' if amount > 0 else 'debt',
            **currency_fields
        })
        # Запись в Сверку
        self.env['amanat.reconciliation'].create({
            'date': order.date,
            'partner_id': partner.id,
            'currency': order.currency,
            'sum': amount,
            'order_id': [(6, 0, [order.id])],
            'wallet_id': self._get_default_wallet().id,
            'sender_id':   [(6, 0, [sender_payer.id])]   if sender_payer   else [],
            'receiver_id': [(6, 0, [receiver_payer.id])] if receiver_payer else [],
            **currency_fields
        })

    def _delete_related_records(self):
        for reserve in self:
            for order in reserve.order_ids:
                # Удаляем деньги
                moneys = self.env['amanat.money'].search([('order_id', '=', order.id)])
                for money in moneys:
                    if money.writeoff_ids:
                        money.writeoff_ids.unlink()
                    money.unlink()
                # Удаляем сверки
                self.env['amanat.reconciliation'].search(
                    [('order_id', '=', order.id)]
                ).unlink()
                # Удаляем сам ордер
                order.unlink()
            reserve.with_context(skip_automation=True).write({'order_ids': [(5, 0, 0)]})

    def _complete_reserve(self):
        pass  # можно дописать при необходимости

    def _get_default_wallet(self):
        wallet = self.env['amanat.wallet'].search([('name', '=', 'Валютный резерв')], limit=1)
        if not wallet:
            wallet = self.env['amanat.wallet'].create({'name': 'Валютный резерв'})
        return wallet

    def _get_default_wallet_id(self):
        wallet = self._get_default_wallet()
        return wallet.id

    def _process_royalty_distribution(self):
        royalty_contragent = self.env['amanat.contragent'].search(
            [('name', '=', 'Роялти')], limit=1
        )
        royalty_payer = self.env['amanat.payer'].search(
            [('contragents_ids', 'in', royalty_contragent.id)], limit=1
        ) if royalty_contragent else False

        old_orders = self.env['amanat.order'].search([
            ('reserve_ids', 'in', self.id),
            ('type', '=', 'royalty')
        ])
        old_orders.mapped('money_ids').unlink()
        old_orders.mapped('sverka_ids').unlink()
        old_orders.unlink()

        for i in (1, 2):
            recipient = getattr(self, f'royalty_recipient_{i}')
            percent   = getattr(self, f'royalty_percent_{i}')
            if recipient and percent and self.amount:
                royalty_sum = -abs(round(self.amount * percent, 2))
                payer2 = self.env['amanat.payer'].search(
                    [('contragents_ids', 'in', recipient.id)], limit=1
                )
                order = self.env['amanat.order'].create({
                    'date': self.today_date,
                    'type': 'royalty',
                    'partner_1_id': royalty_contragent.id,
                    'partner_2_id': recipient.id,
                    'wallet_1_id': self._get_default_wallet_id(),
                    'wallet_2_id': self._get_default_wallet_id(),
                    'payer_1_id': royalty_payer.id if royalty_payer else False,
                    'payer_2_id': payer2.id if payer2 else False,
                    'currency': self.currency,
                    'amount': royalty_sum,
                    'reserve_ids': [(6, 0, [self.id])],
                    'comment': self.comment,
                })
                fields = self._get_currency_fields(self.currency, royalty_sum)
                self.env['amanat.money'].create({
                    'royalty': True,
                    'date': self.today_date,
                    'wallet_id': self._get_default_wallet().id,
                    'partner_id': recipient.id,
                    'currency': self.currency,
                    'amount': royalty_sum,
                    'order_id': order.id,
                    'state': 'debt',
                    **fields
                })
                self.env['amanat.reconciliation'].create({
                    'date': self.today_date,
                    'partner_id': recipient.id,
                    'currency': self.currency,
                    'sum': royalty_sum,
                    'order_id': [(6, 0, [order.id])],
                    'wallet_id': self._get_default_wallet().id,
                    'sender_id':   [(6, 0, [royalty_payer.id])] if royalty_payer else [],
                    'receiver_id': [(6, 0, [payer2.id])]        if payer2         else [],
                    **fields
                })
