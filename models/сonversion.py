from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .base_model import AmanatBaseModel
import logging

_logger = logging.getLogger(__name__)

CURRENCY_SELECTION = [
    ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'),
    ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
    ('usdt', 'USDT'),
    ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
    ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'),
    ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
]

class Conversion(models.Model, AmanatBaseModel):
    _name = 'amanat.conversion'
    _inherit = ['amanat.base.model', 'mail.thread', 'mail.activity.mixin']
    _description = 'Конвертация валют'

    # Many2many relation for extract deliveries
    extract_delivery_ids = fields.Many2many(
        'amanat.extract_delivery',
        'amanat_conversion_extract_delivery_rel',
        'conversion_id',  # column for conversion id in relation table
        'extract_delivery',  # correct column for extract_delivery id
        string='Выписки', tracking=True
    )

    # View aliases for legacy XML
    create_Conversion = fields.Boolean(
        related='create_conversion', readonly=False, string='Создать конвертацию'
    )
    delete_Conversion = fields.Boolean(
        related='delete_conversion', readonly=False, string='Удалить конвертацию'
    )
    has_royalti = fields.Boolean(
        related='has_royalty', readonly=False, string='Есть роялти'
    )
    make_royalti = fields.Boolean(
        related='make_royalty', readonly=False, string='Провести роялти'
    )

    name = fields.Char(
        string='Номер сделки', readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.conversion.sequence')
    )
    state = fields.Selection([
        ('open', 'Открыта'), ('archive', 'Архив'), ('close', 'Закрыта')
    ], string='Статус', default='open', tracking=True)
    date = fields.Date(
        string='Дата', default=fields.Date.context_today, tracking=True
    )
    amount = fields.Float(
        string='Сумма', digits=(16, 2), tracking=True
    )

    currency = fields.Selection(
        CURRENCY_SELECTION, string='Валюта', default='rub', tracking=True
    )
    conversion_currency = fields.Selection(
        CURRENCY_SELECTION, string='В какую валюту', default='rub', tracking=True
    )
    rate = fields.Float(
        string='Курс', digits=(16, 6), tracking=True
    )
    cross_envelope = fields.Boolean(
        string='Кросс-конверт', default=False, tracking=True
    )
    cross_rate = fields.Float(
        string='Кросс-курс', digits=(16, 6), tracking=True
    )
    cross_conversion_currency = fields.Selection(
        [('rub', 'RUB'), ('usd', 'USD')], 
        string='Кросс-валюта', 
        tracking=True,
    )

    sender_id = fields.Many2one(
        'amanat.contragent', string='Отправитель', tracking=True
    )
    sender_payer_id = fields.Many2one(
        'amanat.payer', string='Плательщик отправителя', tracking=True,
        domain="[('contragents_ids','in', sender_id)]"
    )
    receiver_id = fields.Many2one(
        'amanat.contragent', string='Получатель', tracking=True
    )
    receiver_payer_id = fields.Many2one(
        'amanat.payer', string='Плательщик получателя', tracking=True,
        domain="[('contragents_ids','in', receiver_id)]"
    )

    wallet_id = fields.Many2one(
        'amanat.wallet', string='Кошелек', tracking=True
    )
    
    @api.model
    def create(self, vals):
        # Найдём или создадим кошелёк «Неразмеченные»
        Wallet = self.env['amanat.wallet']
        unmarked = Wallet.search([('name', '=', 'Конвертация')], limit=1)
        if not unmarked:
            unmarked = Wallet.create({'name': 'Конвертация'})
        # Если в vals не задан кошелёк отправителя/получателя — подставляем
        if not vals.get('wallet_id'):
            vals['wallet_id'] = unmarked.id
        return super(Conversion, self).create(vals)

    order_id = fields.Many2many(
        'amanat.order', 'amanat_order_conversion_rel', 'conversion_id', 'order_id',
        string='Ордеры', tracking=True
    )

    contragent_count = fields.Selection(
        [('1', '1'), ('2', '2')], string='Кол-во КА', default='1', tracking=True
    )

    create_conversion = fields.Boolean(
        string='Создать конвертацию', default=False, tracking=True
    )
    delete_conversion = fields.Boolean(
        string='Удалить конвертацию', default=False, tracking=True
    )

    has_royalty = fields.Boolean(
        string='Есть роялти', default=False, tracking=True
    )
    make_royalty = fields.Boolean(
        string='Провести роялти', default=False, tracking=True
    )
    royalty_recipient_1 = fields.Many2one(
        'amanat.contragent', string='Получатель роялти 1', tracking=True
    )
    royalty_percent_1 = fields.Float(
        string='% первого', widget='percentage', options="{'rounding': 2}", tracking=True
    )
    royalty_amount_1 = fields.Float(
        string='Сумма роялти 1', compute='_compute_royalty_amount_1', store=True, tracking=True
    )
    royalty_recipient_2 = fields.Many2one(
        'amanat.contragent', string='Получатель роялти 2', tracking=True
    )
    royalty_percent_2 = fields.Float(
        string='% второго', widget='percentage', options="{'rounding': 2}", tracking=True
    )
    royalty_amount_2 = fields.Float(
        string='Сумма роялти 2', compute='_compute_royalty_amount_2', store=True, tracking=True
    )

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

    @api.depends('amount', 'royalty_percent_1')
    def _compute_royalty_amount_1(self):
        """Вычисляет сумму роялти в исходной валюте (как в Airtable)."""
        for rec in self:
            # Для Airtable-подобного поведения просто умножаем исходную сумму на процент
            # (без конвертации валют)
            rec.royalty_amount_1 = rec.amount * rec.royalty_percent_1

    @api.depends('amount', 'royalty_percent_2')
    def _compute_royalty_amount_2(self):
        """Вычисляет сумму роялти в исходной валюте (как в Airtable)."""
        for rec in self:
            # Для Airtable-подобного поведения просто умножаем исходную сумму на процент
            # (без конвертации валют)
            rec.royalty_amount_2 = rec.amount * rec.royalty_percent_2

    @api.onchange('contragent_count', 'sender_id', 'sender_payer_id')
    def _onchange_contragent_count(self):
        for rec in self:
            if rec.contragent_count == '1':
                # Всегда жёстко синхронизируем
                rec.receiver_id = rec.sender_id
                rec.receiver_payer_id = rec.sender_payer_id

            else:  # '2' контрагента
                # Если получатель до сих пор равен отправителю (значит, автозаполнение) – очищаем,
                # иначе считаем, что пользователь уже выбрал нужного получателя и не вмешиваемся.
                if rec.receiver_id == rec.sender_id:
                    rec.receiver_id = False
                if rec.receiver_payer_id == rec.sender_payer_id:
                    rec.receiver_payer_id = False

    @api.model
    def _find_or_create_payer(self, name, contragent_id):
        if not name:
            return False
        payer = self.env['amanat.payer'].search([('name', '=', name)], limit=1)
        return payer or self.env['amanat.payer'].create({
            'name': name,
            'contragents_ids': [(4, contragent_id)]
        })

    def write(self, vals):
        if self.env.context.get('skip_automation'):
            return super(Conversion, self).write(vals)

        do_create = vals.get('create_conversion', False)
        do_royal = vals.get('make_royalty', False)
        do_delete = vals.get('delete_conversion', False)

        res = super(Conversion, self).write(vals)

        recs = self.browse(self.ids)

        for rec in recs:
            if rec.state == 'archive':
                # просто сбрасываем флаги
                rec.with_context(skip_automation=True).write({
                    'create_conversion': False,
                    'make_royalty': False,
                    'delete_conversion': False,
                })
                continue

            if do_create:
                rec.with_context(skip_automation=True)._create_conversion_order()
                rec.with_context(skip_automation=True).write({'create_conversion': False})

            if do_royal:
                rec.with_context(skip_automation=True)._create_royalty_entries()
                rec.with_context(skip_automation=True).write({'make_royalty': False})

            if do_delete:
                rec.with_context(skip_automation=True).action_delete_conversion()
                rec.with_context(skip_automation=True).write({'delete_conversion': False})

        return res


    def action_execute_conversion(self):
        """Создает ордер конвертации и все связанные записи."""
        self.ensure_one()
        if not self.wallet_id:
            raise UserError(_('Не указан кошелек для конвертации.'))
        
        # Формируем комментарий в стиле Airtable
        comment_text = _('Конвертация: %s -> %s, курс: %s') % (
            self.currency, self.conversion_currency, self.rate)
        if self.cross_envelope:
            comment_text += _(' курс-кросс (%s)') % (self.cross_rate)

        # создаём сам ордер
        order = self.env['amanat.order'].create({
            'date':          self.date,
            'type':          'transfer',
            'partner_1_id':  self.sender_id.id,
            'partner_2_id':  self.receiver_id.id,
            'payer_1_id':    self.sender_payer_id.id,
            'payer_2_id':    self.receiver_payer_id.id,
            'wallet_1_id':   self.wallet_id.id,
            'wallet_2_id':   self.wallet_id.id,
            'currency':      self.currency,
            'amount':        self.amount,
            'rate':          self.rate,
            'comment':       comment_text,
        })

        # базовая сумма для конвертации — либо cross_rate, либо amount
        base_amount = self.cross_rate if self.cross_envelope else self.amount

        # считаем результат с учётом направления конвертации
        converted_amount = self._convert_amount(
            amount=base_amount,
            from_currency=self.currency,
            to_currency=self.conversion_currency,
            rate=self.rate
        )

        # создаём записи Money: списание и поступление
        cf_map_out = self._currency_field_map(self.currency, -base_amount)
        cf_map_in  = self._currency_field_map(self.conversion_currency, converted_amount)

        money_vals = [
            {
                'date':      self.date,
                'partner_id': self.sender_id.id,
                'currency':   self.currency,
                'amount':     -base_amount,
                'state':      'debt',
                'wallet_id':  self.wallet_id.id,
                'order_id':   [(6, 0, [order.id])],
                **{k: v for k, v in cf_map_out.items() if k.startswith('sum_')},
            },
            {
                'date':      self.date,
                'partner_id': self.receiver_id.id,
                'currency':   self.conversion_currency,
                'amount':     converted_amount,
                'state':      'positive',
                'wallet_id':  self.wallet_id.id,
                'order_id':   [(6, 0, [order.id])],
                **{k: v for k, v in cf_map_in.items() if k.startswith('sum_')},
            },
        ]
        self.env['amanat.money'].create(money_vals)

        # связываем ордер с конвертацией
        self.order_id = [(4, order.id)]
        return order

    def _currency_field_map(self, currency, amount):
        """Return mapping for currency-specific fields on money and reconciliation models."""
        # e.g. currency 'rub' maps to field 'amount_rub' or 'sum_rub'
        return {
            f'amount_{currency}': amount,
            f'sum_{currency}': amount,
        }
    
    def _clear_royalty_entries(self):
        """Удаляет существующие записи роялти для текущего ордера."""
        if not self.order_id:
            return
            
        order_id = self.order_id[0].id if self.order_id else False
        if not order_id:
            return
            
        # Находим записи Money с флагом роялти
        royalty_money = self.env['amanat.money'].search([
            ('order_id', '=', order_id),
            ('royalty', '=', True)
        ])
        
        # Удаляем найденные записи
        if royalty_money:
            royalty_money.unlink()
            _logger.info('Удалено %d записей роялти для ордера (ID=%s)', len(royalty_money), order_id)

        payer_royalty = self.env['amanat.payer'].search([('name', '=', 'Роялти')], limit=1)
        if payer_royalty:
            royalty_recons = self.env['amanat.reconciliation'].search([
                ('order_id', '=', order_id),
                ('sender_id', 'in', [payer_royalty.id])
            ])
            if royalty_recons:
                royalty_recons.unlink()

    def _clear_orders_money_recon(self):
        """Удаляет все связанные ордера, записи в таблицах Money и Reconciliation"""
        self.ensure_one()
        
        # Проверяем, есть ли у нас связанные ордера
        if not self.order_id:
            _logger.info('Нет ордеров для удаления у конвертации (ID=%s)', self.id)
            return True
            
        order_count = len(self.order_id)
        
        if order_count > 0:
            for order in list(self.order_id):
                order_id = order.id
                
                # Удаляем записи в таблице сверок (Reconciliation)
                recons = self.env['amanat.reconciliation'].search([('order_id', '=', order_id)])
                recon_count = len(recons)
                if recon_count > 0:
                    recons.unlink()
                    _logger.info('Удалено %d записей сверок для ордера (ID=%s)', recon_count, order_id)
                
                # Удаляем записи в таблице денег (Money)
                money_records = self.env['amanat.money'].search([('order_id', '=', order_id)])
                money_count = len(money_records)
                if money_count > 0:
                    money_records.unlink()
                    _logger.info('Удалено %d записей денег для ордера (ID=%s)', money_count, order_id)
                
                # Удаляем сам ордер
                order.unlink()
                _logger.info('Удален ордер (ID=%s)', order_id)
            
            # Очищаем связь с ордерами
            self.order_id = [(5,)]
            _logger.info('Очищены ссылки на ордера в записи конвертации (ID=%s)', self.id)
        
        return True

    def _create_conversion_order(self):
        """Создает ордер конвертации и присваивает его к текущей записи.
        Используется при нажатии на кнопку 'Создать конвертацию'.
        """
        self.ensure_one()
        if not self.wallet_id:
            raise UserError(_('Не указан кошелек для конвертации.'))
        
        # Сначала очищаем существующие ордера и связанные записи
        self._clear_orders_money_recon()

        # Формируем комментарий в стиле Airtable
        comment_text = _('Конвертация: %s -> %s, курс: %s') % (
            self.currency, self.conversion_currency, self.rate)
        if self.cross_envelope:
            comment_text += _(' курс-кросс (%s)') % (self.cross_rate)
        
        # Затем создаем новый ордер
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
            'comment': comment_text,
        })
        
        # Связываем ордер с текущей записью
        self.order_id = [(4, order.id)]
        
        # Создаем записи для нового ордера
        self._post_entries_for_order(order)
        
        return order

    def _post_entries_for_order(self, order):
        """Создает записи в Money и Reconciliation для указанного ордера конвертации."""
        # Use values from order's computed conversion fields
        out_amount = order.amount
        in_amount = order.amount_after_conv

        Money = self.env['amanat.money']
        Recon = self.env['amanat.reconciliation']

        # Build lines depending on contragent_count
        lines = [
            (order.currency, -out_amount, self.sender_payer_id),
            (self.conversion_currency, in_amount, self.sender_payer_id),
        ]
        
        partners = [self.sender_id, self.receiver_id]
        if self.contragent_count == '2':
            _logger.info("Выбраны 2 контрагента")
            lines = [
                (order.currency, -out_amount, self.sender_payer_id, self.receiver_payer_id),
                (self.conversion_currency, in_amount, self.receiver_payer_id, self.sender_payer_id),
                (order.currency, out_amount, self.sender_payer_id, self.receiver_payer_id),
                (self.conversion_currency, -in_amount, self.receiver_payer_id, self.sender_payer_id),
            ]
            partners = [self.sender_id, self.sender_id, self.receiver_id, self.receiver_id]

        for idx, vals in enumerate(lines):
            curr, amt, pay1 = vals[0], vals[1], vals[2]
            pay2 = vals[3] if len(vals) > 3  else pay1
            cf_map = self._currency_field_map(curr, amt)
            money_vals = {
                'date':       order.date,
                'partner_id': partners[idx].id,
                'currency':   curr,
                'amount':     amt,
                'state':      'debt' if amt < 0 else 'positive',
                'wallet_id':  order.wallet_1_id.id,
                'order_id':   order.id,
                **{k: v for k, v in cf_map.items() if k.startswith('sum_')},
            }
            Money.create(money_vals)

            recon_vals = {
                'date':       order.date,
                'partner_id': partners[idx].id,
                'currency':   curr,
                'sum':        amt,
                'wallet_id':  order.wallet_1_id.id,
                'order_id':   [(6, 0, [order.id])],
                'sender_id':  [(6, 0, [pay1.id])],
                'receiver_id':[(6, 0, [pay2.id])],
                **{k: v for k, v in cf_map.items() if k.startswith('sum_')},
            }
            Recon.create(recon_vals)

    def _create_royalty_entries(self):
        """Создает записи роялти на основе суммы роялти в исходной валюте, аналогично Airtable."""
        # Сначала удаляем существующие записи роялти
        self._clear_royalty_entries()

        order = self.order_id and self.order_id[0]
        if not order:
            raise UserError(_('Нельзя создать роялти без ордера'))
        
        # В Airtable роялти создается в исходной валюте (self.currency), 
        # а не в валюте конвертации (self.conversion_currency)
        
        Money = self.env['amanat.money']
        Recon = self.env['amanat.reconciliation']

        # Найдем или создадим "Отправитель роялти" (плательщик)
        RoyaltySender = self.env['amanat.payer'].search([('name', '=', 'Роялти')], limit=1)
        if not RoyaltySender:
            RoyaltySender = self.env['amanat.payer'].create({'name': 'Роялти'})
        
        # Найдем или создадим "Отправитель роялти" (контрагент)
        RoyaltySenderPartner = self.env['amanat.contragent'].search([('name', '=', 'Роялти')], limit=1)
        if not RoyaltySenderPartner:
            RoyaltySenderPartner = self.env['amanat.contragent'].create({'name': 'Роялти'})
            
            # Связываем созданного контрагента с плательщиком, если он был только что создан
            if RoyaltySender and not RoyaltySender.contragents_ids:
                RoyaltySender.write({'contragents_ids': [(4, RoyaltySenderPartner.id)]})
        
        # первый получатель
        if self.royalty_recipient_1 and self.royalty_percent_1:
            # Берем напрямую сумму из поля royalty_amount_1, которое вычисляется 
            # в _compute_royalty_amount_1 и хранится в базе
            amt1 = self.royalty_amount_1
            
            payer1 = self._find_or_create_payer(
                self.royalty_recipient_1.name, self.royalty_recipient_1.id
            )
            partner1 = payer1.contragents_ids and payer1.contragents_ids[0].id or self.royalty_recipient_1.id

            # Используем исходную валюту (как в Airtable)
            cf_map_1 = self._currency_field_map(self.currency, -amt1)
            money_vals = {
                'date':       self.date,
                'partner_id': partner1,  # Получатель роялти (контрагент)
                'currency':   self.currency,  # Используем исходную валюту
                'amount':     -amt1,
                'state':      'debt',
                'wallet_id':  self.wallet_id.id,
                'order_id':   order.id,
                'royalty':    True,  # Помечаем запись как роялти
                **{k: v for k, v in cf_map_1.items() if k.startswith('sum_')},
            }
            Money.create(money_vals)

            recon_vals = {
                'date':       self.date,
                'partner_id': RoyaltySenderPartner.id,  # Устанавливаем "Отправитель роялти" как контрагента
                'currency':   self.currency,  # Используем исходную валюту
                'sum':        -amt1,
                'wallet_id':  self.wallet_id.id,
                'order_id':   [(6, 0, [order.id])],
                # вот эти поля и заполняют колонки «Отправитель»/«Получатель»
                'sender_id':   [(6, 0, [RoyaltySender.id])],  # Отправитель роялти (плательщик)
                'receiver_id': [(6, 0, [payer1.id])],  # Получатель роялти (плательщик)
                # Удалено поле royalty, которого нет в модели
                **{k: v for k, v in cf_map_1.items() if k.startswith('sum_')},
            }
            Recon.create(recon_vals)

        # второй получатель
        if self.royalty_recipient_2 and self.royalty_percent_2:
            # Берем напрямую сумму из поля royalty_amount_2
            amt2 = self.royalty_amount_2
            
            payer2 = self._find_or_create_payer(
                self.royalty_recipient_2.name, self.royalty_recipient_2.id
            )
            partner2 = payer2.contragents_ids and payer2.contragents_ids[0].id or self.royalty_recipient_2.id

            # Используем исходную валюту (как в Airtable)
            cf_map_2 = self._currency_field_map(self.currency, -amt2)
            money_vals = {
                'date':       self.date,
                'partner_id': partner2,  # Получатель роялти (контрагент)
                'currency':   self.currency,  # Используем исходную валюту
                'amount':     -amt2,
                'state':      'debt',
                'wallet_id':  self.wallet_id.id,
                'order_id':   order.id,
                'royalty':    True,  # Помечаем запись как роялти
                **{k: v for k, v in cf_map_2.items() if k.startswith('sum_')},
            }
            Money.create(money_vals)

            recon_vals = {
                'date':       self.date,
                'partner_id': RoyaltySenderPartner.id,  # Устанавливаем "Отправитель роялти" как контрагента
                'currency':   self.currency,  # Используем исходную валюту
                'sum':        -amt2,
                'wallet_id':  self.wallet_id.id,
                'order_id':   [(6, 0, [order.id])],
                # вот эти поля и заполняют колонки «Отправитель»/«Получатель»
                'sender_id':   [(6, 0, [RoyaltySender.id])],  # Отправитель роялти (плательщик)
                'receiver_id': [(6, 0, [payer2.id])],  # Получатель роялти (плательщик)
                # Удалено поле royalty, которого нет в модели
                **{k: v for k, v in cf_map_2.items() if k.startswith('sum_')},
            }
            Recon.create(recon_vals)

    def _convert_amount(self, amount, from_currency, to_currency, rate):
        """
        Конвертирует сумму из одной валюты в другую.
        Делим, если направление между группами base_div ↔ target_div,
        иначе умножаем.
        """
        if not rate:
            rate = 1.0

        base_div   = {'rub', 'rub_cashe', 'thb', 'thb_cashe', 'aed', 'aed_cashe'}
        target_div = {'usd', 'usd_cashe', 'euro', 'euro_cashe', 'usdt', 'cny', 'cny_cashe'}

        # проверяем, попадают ли валюты в разные группы
        is_cross_group = (
            (from_currency in base_div   and to_currency in target_div) or
            (from_currency in target_div and to_currency in base_div)
        )

        if is_cross_group:
            return amount / rate
        else:
            return amount * rate

    def action_delete_conversion(self):
        self.ensure_one()
        _logger.info('Удаление конвертации ID=%s начато.', self.id)
        try:
            self.with_context(skip_automation=True)._clear_orders_money_recon()
            self.with_context(skip_automation=True).write({'state': 'archive'})
            _logger.info('Успешно удалена конвертация ID=%s', self.id)
            return True
        except Exception as e:
            _logger.error('Ошибка при удалении конвертации ID=%s: %s', self.id, str(e))
            raise UserError(_('Ошибка при удалении конвертации: %s') % str(e))