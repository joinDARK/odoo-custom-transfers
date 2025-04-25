from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .base_model import AmanatBaseModel

CURRENCY_SELECTION = [
    ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'),
    ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
    ('usdt', 'USDT'),
    ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
    ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'),
    ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
    ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
]

class Conversion(models.Model, AmanatBaseModel):
    _name = 'amanat.conversion'
    _inherit = ['amanat.base.model', 'mail.thread', 'mail.activity.mixin']
    _description = 'Конвертация валют'

    name = fields.Char(
        string='Номер сделки',
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.conversion.sequence'),
        readonly=True,
    )
    state = fields.Selection(
        [('open', 'Открыта'), ('archive', 'Архив'), ('close', 'Закрыта')],
        string='Статус', default='open', tracking=True
    )

    date = fields.Date(string='Дата', default=fields.Date.context_today, tracking=True)
    amount = fields.Float(string='Сумма', tracking=True, digits=(16, 2))

    currency = fields.Selection(CURRENCY_SELECTION, string='Валюта', default='rub', tracking=True)
    conversion_currency = fields.Selection(CURRENCY_SELECTION, string='В какую валюту', default='rub', tracking=True)

    sender_id = fields.Many2one('amanat.contragent', string='Отправитель', tracking=True)
    sender_payer_id = fields.Many2one(
        'amanat.payer', string='Плательщик отправителя', tracking=True,
        domain="[('contragents_ids','in',sender_id)]"
    )
    receiver_id = fields.Many2one('amanat.contragent', string='Получатель', tracking=True)
    receiver_payer_id = fields.Many2one(
        'amanat.payer', string='Плательщик получателя', tracking=True,
        domain="[('contragents_ids','in',receiver_id)]"
    )

    rate = fields.Float(string='Курс', tracking=True, digits=(16, 6))
    wallet_id = fields.Many2one('amanat.wallet', string='Кошелек', tracking=True)
    order_id = fields.Many2many(
        'amanat.order', 'amanat_order_conversion_rel',
        'conversion_id', 'order_id', string='Ордеры', tracking=True
    )
    contragent_count = fields.Selection(
        [('1','1'),('2','2')], string='Колво КА', default='1', tracking=True
    )

    create_Conversion = fields.Boolean(string='Создать', default=False, tracking=True)
    delete_Conversion = fields.Boolean(string='Удалить', default=False, tracking=True)

    cross_envelope = fields.Boolean(string='Кросс-конверт', default=False, tracking=True)
    cross_rate = fields.Float(string='Кросс-курс', tracking=True, digits=(16, 6))

    extract_delivery_ids = fields.Many2many(
        'amanat.extract_delivery', 'amanat_conversion_extract_delivery_rel',
        'conversion_id', 'extract_delivery', string='Выписка разнос',
        domain=[('direction_choice','=','conversion')], tracking=True
    )

    has_royalti = fields.Boolean(string='Есть роялти', default=False, tracking=True)
    make_royalti = fields.Boolean(string='Провести роялти', default=False, tracking=True)
    royalty_recipient_1 = fields.Many2one('amanat.contragent', string='Получатель роялти 1', tracking=True)
    royalty_percent_1 = fields.Float(
        string='% первого', widget='percentage', options="{'rounding': 2}", tracking=True
    )
    royalty_amount_1 = fields.Float(
        string='Сумма роялти 1', compute='_compute_royalty_amount_1', store=True, tracking=True
    )
    royalty_recipient_2 = fields.Many2one('amanat.contragent', string='Получатель роялти 2', tracking=True)
    royalty_percent_2 = fields.Float(
        string='% второго', widget='percentage', options="{'rounding': 2}", tracking=True
    )
    royalty_amount_2 = fields.Float(
        string='Сумма роялти 2', compute='_compute_royalty_amount_2', store=True, tracking=True
    )

    @api.depends('amount', 'royalty_percent_1')
    def _compute_royalty_amount_1(self):
        for rec in self:
            rec.royalty_amount_1 = rec.amount * rec.royalty_percent_1

    @api.depends('amount', 'royalty_percent_2')
    def _compute_royalty_amount_2(self):
        for rec in self:
            rec.royalty_amount_2 = rec.amount * rec.royalty_percent_2

    @api.model
    def _find_or_create_payer(self, name, contragent_id):
        if not name:
            return False
        Payer = self.env['amanat.payer']
        return Payer.search([('name', '=', name)], limit=1) or Payer.create({
            'name': name,
            'contragents_ids': [(4, contragent_id)],
        })

    def write(self, vals):
        if self.env.context.get('skip_automation'):
            return super().write(vals)
        res = super().write(vals)
        for rec in self:
            if vals.get('create_Conversion') or (not vals and rec.create_Conversion):
                rec.action_execute_conversion()
                rec.with_context(skip_automation=True).write({'create_Conversion': False})
            if vals.get('make_royalti') and rec.has_royalti:
                rec._create_royalti_entries()
                rec.with_context(skip_automation=True).write({'make_royalti': False})
            if vals.get('delete_Conversion') or (not vals and rec.delete_Conversion):
                rec.action_delete_conversion()
        return res

    def action_execute_conversion(self):
        self.ensure_one()
        if not self.wallet_id:
            raise UserError(_('Не указан кошелек для конвертации.'))
        # Очищаем и создаем ордер + записи
        self._clear_orders_money_recon()
        self._create_conversion_order()
        return True

    def _clear_orders_money_recon(self):
        for order in self.order_id:
            self.env['amanat.reconciliation'].search([('order_id', '=', order.id)]).unlink()
            self.env['amanat.money'].search([('order_id', '=', order.id)]).unlink()
            order.unlink()
        self.order_id = [(5,)]

    def _create_conversion_order(self):
        comment = _('Конвертация: %s → %s, курс: %s') % (
            self.currency, self.conversion_currency, self.rate
        )
        order = self.env['amanat.order'].create({
            'date': self.date,
            'type': 'transfer',
            'partner_1_id': self.sender_id.id,
            'partner_2_id': self.receiver_id.id,
            'payer_1_id': self.sender_payer_id.id,
            'payer_2_id': self.receiver_payer_id.id,
            'wallet_1_id': self.wallet_id.id,
            'wallet_2_id': self.wallet_id.id,
            'currency': self.currency,
            'amount': self.amount,
            'rate': self.rate,
            'comment': comment,
        })
        self.order_id = [(4, order.id)]
        self._post_entries_for_order(order)

    def _post_entries_for_order(self, order):
        amt1, amt2 = order.amount_1, order.amount_after_conv
        Money = self.env['amanat.money']
        Recon = self.env['amanat.reconciliation']
        if self.contragent_count == '1':
            lines = [
                (self.currency, -amt1, self.sender_payer_id),
                (self.conversion_currency, amt2, self.sender_payer_id)
            ]
            partners = [self.sender_id, self.sender_id]
        else:
            lines = [
                (self.currency, -amt1, self.sender_payer_id, self.receiver_payer_id),
                (self.conversion_currency, amt2, self.sender_payer_id, self.receiver_payer_id),
                (self.currency, amt1, self.sender_payer_id, self.receiver_payer_id),
                (self.conversion_currency, -amt2, self.sender_payer_id, self.receiver_payer_id),
            ]
            partners = [self.sender_id, self.sender_id, self.receiver_id, self.receiver_id]
        for idx, vals in enumerate(lines):
            curr, sign = vals[0], vals[1]
            pay1 = vals[2]
            pay2 = vals[3] if len(vals) > 3 else pay1
            partner = partners[idx]
            money_vals = {
                'date': self.date,
                'partner_id': partner.id,
                'currency': curr,
                'amount': sign,
                'state': 'debt' if sign < 0 else 'positive',
                'wallet_id': self.wallet_id.id,
                'order_id': [(6, 0, [order.id])],
                **self._currency_field_map(curr, sign)
            }
            Money.create(money_vals)
            Recon.create({
                'date': self.date,
                'partner_id': partner.id,
                'currency': curr,
                'sum': sign,
                'wallet_id': self.wallet_id.id,
                'order_id': [(6, 0, [order.id])],
                'sender_id': [(6, 0, [pay1.id])],
                'receiver_id': [(6, 0, [pay2.id])],
                **self._currency_field_map(curr, sign)
            })

    def _create_royalti_entries(self):
        order = self.order_id and self.order_id[0]
        if not order:
            raise UserError(_('Нельзя создать роялти без созданного ордера.'))
        amt = self.royalty_amount_1
        curr = self.currency
        payer = self._find_or_create_payer(
            self.royalty_recipient_1.name,
            self.royalty_recipient_1.id
        )
        Money = self.env['amanat.money']
        Recon = self.env['amanat.reconciliation']
        money_vals = {
            'date': self.date,
            'partner_id': self.royalty_recipient_1.id,
            'currency': curr,
            'amount': -amt,
            'state': 'debt',
            'wallet_id': self.wallet_id.id,
            'order_id': [(6, 0, [order.id])],
            **self._currency_field_map(curr, -amt)
        }
        Money.create(money_vals)
        Recon.create({
            'date': self.date,
            'partner_id': self.royalty_recipient_1.id,
            'currency': curr,
            'sum': -amt,
            'wallet_id': self.wallet_id.id,
            'order_id': [(6, 0, [order.id])],
            'sender_id': [(6, 0, [payer.id])],
            'receiver_id': [(6, 0, [payer.id])],
            **self._currency_field_map(curr, -amt)
        })

    def action_delete_conversion(self):
        super().action_delete_conversion()

    @api.model
    def _currency_field_map(self, code, amount):
        mapping = {
            'rub': 'sum_rub', 'rub_cashe': 'sum_rub_cashe',
            'usd': 'sum_usd', 'usd_cashe': 'sum_usd_cashe',
            'usdt': 'sum_usdt', 'euro': 'sum_euro',
            'euro_cashe': 'sum_euro_cashe', 'cny': 'sum_cny',
            'cny_cashe': 'sum_cny_cashe', 'aed': 'sum_aed',
            'aed_cashe': 'sum_aed_cashe', 'thb': 'sum_thb',
            'thb_cashe': 'sum_thb_cashe',
        }
        field = mapping.get(code)
        return {field: amount} if field else {}
