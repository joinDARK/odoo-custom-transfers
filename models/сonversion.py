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
        string='Сумма', digits=(16, 6), tracking=True
    )

    currency = fields.Selection(
        CURRENCY_SELECTION, string='Валюта', default='usd', tracking=True
    )
    conversion_currency = fields.Selection(
        CURRENCY_SELECTION, string='В какую валюту', default='rub', tracking=True
    )
    rate = fields.Float(
        string='Курс', digits=(16, 8), tracking=True
    )
    cross_envelope = fields.Boolean(
        string='Кросс-конверт', default=False, tracking=True
    )
    cross_rate = fields.Float(
        string='Кросс-курс', digits=(16, 8), tracking=True
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

    make_royalty = fields.Boolean(
        string='Провести роялти', default=False, tracking=True
    )
    royalty_recipient_1 = fields.Many2one(
        'amanat.contragent', string='Получатель роялти 1', tracking=True
    )
    royalty_percent_1 = fields.Float(
        string='% первого', digits=(16, 8), tracking=True
    )
    royalty_amount_1 = fields.Float(
        string='Сумма роялти 1', 
        compute='_compute_royalty_amount_1', 
        store=True,
        digits=(16, 6),
        tracking=True,
        readonly=False,
    )
    royalty_recipient_2 = fields.Many2one(
        'amanat.contragent', string='Получатель роялти 2', tracking=True
    )
    royalty_percent_2 = fields.Float(
        string='% второго', digits=(16, 8), tracking=True
    )
    royalty_amount_2 = fields.Float(
        string='Сумма роялти 2', 
        compute='_compute_royalty_amount_2', 
        store=True, 
        digits=(16, 6),
        tracking=True,
        readonly=False,
    )

    royalty_recipient_3 = fields.Many2one(
        'amanat.contragent', string='Получатель роялти 3', tracking=True
    )
    royalty_percent_3 = fields.Float(
        string='% первого', digits=(16, 8), tracking=True
    )
    royalty_amount_3 = fields.Float(
        string='Сумма роялти 3', 
        compute='_compute_royalty_amount_3', 
        store=True,
        digits=(16, 6),
        tracking=True,
        readonly=False,
    )
    royalty_recipient_4 = fields.Many2one(
        'amanat.contragent', string='Получатель роялти 4', tracking=True
    )
    royalty_percent_4 = fields.Float(
        string='% второго', digits=(16, 8), tracking=True
    )
    royalty_amount_4 = fields.Float(
        string='Сумма роялти 4', 
        compute='_compute_royalty_amount_4', 
        store=True, 
        digits=(16, 6),
        tracking=True,
        readonly=False,
    )

    royalty_recipient_5 = fields.Many2one(
        'amanat.contragent', string='Получатель роялти 5', tracking=True
    )
    royalty_percent_5 = fields.Float(
        string='% первого', digits=(16, 8), tracking=True
    )
    royalty_amount_5 = fields.Float(
        string='Сумма роялти 5', 
        compute='_compute_royalty_amount_5', 
        store=True,
        digits=(16, 6),
        tracking=True,
        readonly=False,
    )

    comment = fields.Text(
        string='Комментарий', tracking=True
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
    
    @api.depends('amount', 'royalty_percent_3')
    def _compute_royalty_amount_3(self):
        """Вычисляет сумму роялти в исходной валюте (как в Airtable)."""
        for rec in self:
            # Для Airtable-подобного поведения просто умножаем исходную сумму на процент
            # (без конвертации валют)
            rec.royalty_amount_3 = rec.amount * rec.royalty_percent_3

    @api.depends('amount', 'royalty_percent_4')
    def _compute_royalty_amount_4(self):
        """Вычисляет сумму роялти в исходной валюте (как в Airtable)."""
        for rec in self:
            # Для Airtable-подобного поведения просто умножаем исходную сумму на процент
            # (без конвертации валют)
            rec.royalty_amount_4 = rec.amount * rec.royalty_percent_4

    @api.depends('amount', 'royalty_percent_5')
    def _compute_royalty_amount_5(self):
        """Вычисляет сумму роялти в исходной валюте (как в Airtable)."""
        for rec in self:
            # Для Airtable-подобного поведения просто умножаем исходную сумму на процент
            # (без конвертации валют)
            rec.royalty_amount_5 = rec.amount * rec.royalty_percent_5

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
        # Отладка: логируем контекст
        if self.env.context.get('skip_automation'):
            _logger.info('ОТЛАДКА: skip_automation=True в контексте, автоматизация пропущена. Контекст: %s', self.env.context)
            return super(Conversion, self).write(vals)
        
        # Отладка: логируем какие поля изменяются
        automation_fields = ['create_conversion', 'make_royalty', 'delete_conversion']
        changed_automation = {k: v for k, v in vals.items() if k in automation_fields}
        if changed_automation:
            _logger.info('ОТЛАДКА: Изменяются поля автоматизации: %s', changed_automation)

        do_create = vals.get('create_conversion', False)
        do_royal = vals.get('make_royalty', False)
        do_delete = vals.get('delete_conversion', False)

        res = super(Conversion, self).write(vals)

        recs = self.browse(self.ids)

        for rec in recs:
            _logger.info('ОТЛАДКА: Обрабатывается запись ID=%s, состояние=%s', rec.id, rec.state)
            
            if rec.state == 'archive':
                _logger.info('ОТЛАДКА: Запись в архиве, просто сбрасываем флаги')
                # просто сбрасываем флаги
                rec.with_context(skip_automation=True).write({
                    'create_conversion': False,
                    'make_royalty': False,
                    'delete_conversion': False,
                })
                continue

            if do_create:
                _logger.info('ОТЛАДКА: Выполняется create_conversion для записи ID=%s', rec.id)
                rec.with_context(skip_automation=True)._create_conversion_order()
                rec.with_context(skip_automation=True).write({'create_conversion': False})

            if do_royal:
                _logger.info('ОТЛАДКА: Выполняется make_royalty для записи ID=%s', rec.id)
                rec.with_context(skip_automation=True)._create_royalty_entries()
                rec.with_context(skip_automation=True).write({'make_royalty': False})

            if do_delete:
                _logger.info('ОТЛАДКА: Выполняется delete_conversion для записи ID=%s', rec.id)
                rec.with_context(skip_automation=True).action_delete_conversion()
                rec.with_context(skip_automation=True).write({'delete_conversion': False})

        return res

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
        
        # Добавляем комментарий из поля comment модели, если он есть
        if self.comment:
            comment_text += '; %s' % self.comment
        
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

        print('do_royal automation')

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
                'partner_id': partner1,  # Используем ID контрагента, а не плательщика
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
                'partner_id': partner2,  # Используем ID контрагента, а не плательщика
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

        # третий получатель
        if self.royalty_recipient_3 and self.royalty_percent_3:
            amt3 = self.royalty_amount_3
            payer3 = self._find_or_create_payer(
                self.royalty_recipient_3.name, self.royalty_recipient_3.id
            )
            partner3 = payer3.contragents_ids and payer3.contragents_ids[0].id or self.royalty_recipient_3.id

            cf_map_3 = self._currency_field_map(self.currency, -amt3)
            money_vals = {
                'date':       self.date,
                'partner_id': partner3,  # Получатель роялти (контрагент)
                'currency':   self.currency,  # Используем исходную валюту
                'amount':     -amt3,
                'state':      'debt',
                'wallet_id':  self.wallet_id.id,
                'order_id':   order.id,
                'royalty':    True,  # Помечаем запись как роялти
                **{k: v for k, v in cf_map_3.items() if k.startswith('sum_')},
            }
            Money.create(money_vals)

            recon_vals = {
                'date':       self.date,
                'partner_id': partner3,  # Используем ID контрагента, а не плательщика
                'currency':   self.currency,  # Используем исходную валюту
                'sum':        -amt3,
                'wallet_id':  self.wallet_id.id,
                'order_id':   [(6, 0, [order.id])],
                'sender_id':   [(6, 0, [RoyaltySender.id])],  # Отправитель роялти (плательщик)
                'receiver_id': [(6, 0, [payer3.id])],  # Получатель роялти (плательщик)
                **{k: v for k, v in cf_map_3.items() if k.startswith('sum_')},
            }
            Recon.create(recon_vals)

        # четвертый получатель
        if self.royalty_recipient_4 and self.royalty_percent_4:
            amt4 = self.royalty_amount_4
            payer4 = self._find_or_create_payer(
                self.royalty_recipient_4.name, self.royalty_recipient_4.id
            )
            partner4 = payer4.contragents_ids and payer4.contragents_ids[0].id or self.royalty_recipient_4.id

            cf_map_4 = self._currency_field_map(self.currency, -amt4)
            money_vals = {
                'date':       self.date,
                'partner_id': partner4,  # Получатель роялти (контрагент)
                'currency':   self.currency,  # Используем исходную валюту
                'amount':     -amt4,
                'state':      'debt',
                'wallet_id':  self.wallet_id.id,
                'order_id':   order.id,
                'royalty':    True,  # Помечаем запись как роялти
                **{k: v for k, v in cf_map_4.items() if k.startswith('sum_')},
            }
            Money.create(money_vals)

            recon_vals = {
                'date':       self.date,
                'partner_id': partner4,  # Используем ID контрагента, а не плательщика
                'currency':   self.currency,  # Используем исходную валюту
                'sum':        -amt4,
                'wallet_id':  self.wallet_id.id,
                'order_id':   [(6, 0, [order.id])],
                'sender_id':   [(6, 0, [RoyaltySender.id])],  # Отправитель роялти (плательщик)
                'receiver_id': [(6, 0, [payer4.id])],  # Получатель роялти (плательщик)
                **{k: v for k, v in cf_map_4.items() if k.startswith('sum_')},
            }
            Recon.create(recon_vals)
        
        # пятый получатель
        if self.royalty_recipient_5 and self.royalty_percent_5:
            amt5 = self.royalty_amount_5
            payer5 = self._find_or_create_payer(
                self.royalty_recipient_5.name, self.royalty_recipient_5.id
            )
            partner5 = payer5.contragents_ids and payer5.contragents_ids[0].id or self.royalty_recipient_5.id

            cf_map_5 = self._currency_field_map(self.currency, -amt5)
            money_vals = {
                'date':       self.date,
                'partner_id': partner5,  # Получатель роялти (контрагент)
                'currency':   self.currency,  # Используем исходную валюту
                'amount':     -amt5,
                'state':      'debt',
                'wallet_id':  self.wallet_id.id,
                'order_id':   order.id,
                'royalty':    True,  # Помечаем запись как роялти
                **{k: v for k, v in cf_map_5.items() if k.startswith('sum_')},
            }
            Money.create(money_vals)

            recon_vals = {
                'date':       self.date,
                'partner_id': partner5,  # Используем ID контрагента, а не плательщика
                'currency':   self.currency,  # Используем исходную валюту
                'sum':        -amt5,
                'wallet_id':  self.wallet_id.id,
                'order_id':   [(6, 0, [order.id])],
                'sender_id':   [(6, 0, [RoyaltySender.id])],  # Отправитель роялти (плательщик)
                'receiver_id': [(6, 0, [payer5.id])],  # Получатель роялти (плательщик)
                **{k: v for k, v in cf_map_5.items() if k.startswith('sum_')},
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

    @api.onchange('sender_id', 'receiver_id', 'date')
    def _onchange_partners_auto_royalty(self):
        """Автоматическое заполнение роялти на основе прайс-листа роялти для конвертаций"""
        if not self.sender_id or not self.receiver_id or not self.date:
            return

        # Ищем подходящие записи в прайс-листе роялти
        domain = [
            ('operation_type', '=', 'conversion'),  # Тип операции = Конвертации
            '|', '|',  # Три условия через ИЛИ
            # 1. Тип участника = "Отправитель" И контрагент = отправитель конвертации
            '&', ('participant_type', '=', 'sender'), ('contragent_id', '=', self.sender_id.id),
            # 2. Тип участника = "Получатель" И контрагент = получатель конвертации  
            '&', ('participant_type', '=', 'recipient'), ('contragent_id', '=', self.receiver_id.id),
            # 3. Тип участника = "Отправитель или получатель" И контрагент = любой из участников
            '&', ('participant_type', '=', 'both'), 
            '|', ('contragent_id', '=', self.sender_id.id), ('contragent_id', '=', self.receiver_id.id)
        ]

        # Добавляем фильтрацию по датам (если указаны)
        date_domain = []
        date_domain.append('|')
        date_domain.append('&')
        date_domain.append('&')
        date_domain.append(('date_from', '!=', False))
        date_domain.append(('date_to', '!=', False))
        date_domain.append('&')
        date_domain.append(('date_from', '<=', self.date))
        date_domain.append(('date_to', '>=', self.date))
        date_domain.append('|')
        date_domain.append(('date_from', '=', False))
        date_domain.append(('date_to', '=', False))

        full_domain = domain + date_domain

        royalty_records = self.env['amanat.price_list_royalty'].search(full_domain)

        # Логирование для отладки
        _logger.info(f"Автоматизация роялти для конвертации: отправитель={self.sender_id.name}, получатель={self.receiver_id.name}, дата={self.date}")
        _logger.info(f"Найдено записей в прайс-листе роялти: {len(royalty_records)}")
        
        if royalty_records:
            # Очищаем старые значения роялти
            for i in range(1, 6):
                setattr(self, f'royalty_percent_{i}', 0.0)
                setattr(self, f'royalty_recipient_{i}', False)

            # Заполняем новые значения роялти (максимум 5)
            for index, record in enumerate(royalty_records[:5], 1):
                setattr(self, f'royalty_percent_{index}', record.royalty_percentage)
                setattr(self, f'royalty_recipient_{index}', record.royalty_recipient_id.id)
                _logger.info(f"Конвертация роялти {index}: {record.royalty_percentage*100:.2f}% для {record.royalty_recipient_id.name} (тип участника: {record.participant_type})")
        else:
            # Очищаем поля роялти если ничего не найдено
            for i in range(1, 6):
                setattr(self, f'royalty_percent_{i}', 0.0)
                setattr(self, f'royalty_recipient_{i}', False)
            _logger.info("Подходящие записи роялти для конвертации не найдены, поля очищены")