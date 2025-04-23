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

    def write(self, vals):
        if self.env.context.get('skip_automation'):
            return super().write(vals)
        res = super().write(vals)
        for rec in self:
        # Создание конверсии
            if vals.get('create_Conversion') or (not vals and rec.create_Conversion):
                rec.action_execute_conversion()
                rec.with_context(skip_automation=True).write({'create_Conversion': False})
            # Удаление конверсии
            if vals.get('delete_Conversion') or (not vals and rec.delete_Conversion):
                rec.action_delete_conversion()
        return res

    def action_execute_conversion(self):
        self.ensure_one()
        if not self.wallet_id:
            raise UserError(_('Не указан кошелек для конвертации.'))
        # Удаляем предыдущие записи
        for order in self.order_id:
            self.env['amanat.reconciliation'].search([('order_id', '=', order.id)]).unlink()
            self.env['amanat.money'].search([('order_id', '=', order.id)]).unlink()
            order.unlink()
        self.order_id = [(5,)]
        # Создаём новый ордер
        comment = _('Конвертация: %s → %s, курс: %s') % (
            self.currency, self.conversion_currency, self.rate
        )
        new_order = self.env['amanat.order'].create({
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
        self.order_id = [(4, new_order.id)]
        # Рассчитываем суммы
        amt1, amt2 = new_order.amount_1, new_order.amount_after_conv
        Money = self.env['amanat.money']
        Recon = self.env['amanat.reconciliation']
        if self.contragent_count == '1':
            # Списание исходной
            money_vals = {
                'date': self.date,
                'partner_id': self.sender_id.id,
                'currency': self.currency,
                'amount': -amt1,
                'state': 'debt',
                'wallet_id': self.wallet_id.id,
                'order_id': [(6, 0, [new_order.id])],
                **self._currency_field_map(self.currency, -amt1)
            }
            Money.create(money_vals)
            recon_vals = {
                'date': self.date,
                'partner_id': self.sender_id.id,
                'currency': self.currency,
                'sum': -amt1,
                'wallet_id': self.wallet_id.id,
                'order_id': [(6, 0, [new_order.id])],
                'sender_id': [(6, 0, [self.sender_payer_id.id])],
                'receiver_id': [(6, 0, [self.sender_payer_id.id])],
                **self._currency_field_map(self.currency, -amt1)
            }
            Recon.create(recon_vals)
            # Зчисление целевой
            money_vals = {
                'date': self.date,
                'partner_id': self.sender_id.id,
                'currency': self.conversion_currency,
                'amount': amt2,
                'state': 'positive',
                'wallet_id': self.wallet_id.id,
                'order_id': [(6, 0, [new_order.id])],
                **self._currency_field_map(self.conversion_currency, amt2)
            }
            Money.create(money_vals)
            recon_vals = {
                'date': self.date,
                'partner_id': self.sender_id.id,
                'currency': self.conversion_currency,
                'sum': amt2,
                'wallet_id': self.wallet_id.id,
                'order_id': [(6, 0, [new_order.id])],
                'sender_id': [(6, 0, [self.sender_payer_id.id])],
                'receiver_id': [(6, 0, [self.sender_payer_id.id])],
                **self._currency_field_map(self.conversion_currency, amt2)
            }
            Recon.create(recon_vals)
        else:
            for partner, curr, sign, s_payer, r_payer in [
                (self.sender_id, self.currency, -amt1, self.sender_payer_id, self.receiver_payer_id),
                (self.sender_id, self.conversion_currency, amt2, self.sender_payer_id, self.receiver_payer_id),
                (self.receiver_id, self.currency, amt1, self.sender_payer_id, self.receiver_payer_id),
                (self.receiver_id, self.conversion_currency, -amt2, self.sender_payer_id, self.receiver_payer_id),
            ]:
                money_vals = {
                    'date': self.date,
                    'partner_id': partner.id,
                    'currency': curr,
                    'amount': sign,
                    'state': 'debt' if sign < 0 else 'positive',
                    'wallet_id': self.wallet_id.id,
                    'order_id': [(6, 0, [new_order.id])],
                    **self._currency_field_map(curr, sign)
                }
                Money.create(money_vals)
                recon_vals = {
                    'date': self.date,
                    'partner_id': partner.id,
                    'currency': curr,
                    'sum': sign,
                    'wallet_id': self.wallet_id.id,
                    'order_id': [(6, 0, [new_order.id])],
                    'sender_id': [(6, 0, [s_payer.id])] if s_payer else [],
                    'receiver_id': [(6, 0, [r_payer.id])] if r_payer else [],
                    **self._currency_field_map(curr, sign)
                }
                Recon.create(recon_vals)
        return True

    def action_delete_conversion(self):
        """
        Удаляет все связанные ордера, контейнеры денег и записи сверки для конверсии.
        """
        self.ensure_one()
        # Удаляем связанные ордера и финансовые записи
        for order in self.order_id:
            # Контейнеры денег
            monies = self.env['amanat.money'].search([('order_id','in',[order.id])])
            for money in monies:
                if hasattr(money,'writeoff_ids') and money.writeoff_ids:
                    money.writeoff_ids.unlink()
                money.unlink()
            # Сверки
            self.env['amanat.reconciliation'].search([('order_id','=',order.id)]).unlink()
            # Ордер
            order.unlink()
        # Сброс связи ордеров
        self.order_id = [(5,)]
        # Архивируем заявку (снимаем флаг и ставим статус)
        super(Conversion,self).write({
            'delete_Conversion': False,
            'state': 'archive'
        })

        return True

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
